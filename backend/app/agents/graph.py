"""LangGraph multi-agent orchestration."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.guardrails import _canon_amount, _expand_allowed, _normalize_amount, apply_guardrail
from app.agents.llm import AgentOutput, LLMFn, call_agent_llm
from app.agents.router import route_query
from app.agents import tools
from app.engines.budget import fifty_thirty_twenty
from app.engines.debt import Debt, payoff_schedule
from app.engines.investment import blended_expected_return, project_growth, risk_allocation
from app.engines.portfolio import load_returns_csv, optimize_portfolio
from app.engines.tax_india import compare_regimes, epf_projection, load_tax_config, nps_projection, sip_maturity
from app.core.paths import config_path
from app.rag.retriever import retrieve


class GraphState(TypedDict, total=False):
    user_id: int
    query: str
    route: list[str]
    tool_results: dict[str, Any]
    rag_chunks: list[dict[str, Any]]
    agent_outputs: dict[str, dict[str, Any]]
    answer: dict[str, Any]
    disclaimers: list[str]
    params: dict[str, Any]


def _dec(v: Any) -> str:
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    return str(v)


async def _gather_context(
    db: AsyncSession,
    user_id: int,
    query: str,
    routes: list[str],
    params: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    params = params or {}
    ctx: dict[str, Any] = {"profile": await tools.get_profile(db, user_id)}
    mom = await tools.month_over_month(db, user_id, 6)
    ctx["month_over_month"] = [
        {**m, "income": _dec(m["income"]), "expenses": _dec(m["expenses"]), "surplus": _dec(m["surplus"])}
        for m in mom
    ]
    spend_label, spend = await tools.spend_by_category_recent(db, user_id, 3)
    ctx["spend_by_category"] = {k: _dec(v) for k, v in spend.items()}
    ctx["spend_window"] = spend_label
    if "budget_agent" in routes and ctx["profile"] and spend:
        budget = fifty_thirty_twenty(ctx["profile"]["monthly_income"], spend)
        ctx["budget"] = {
            "actual": {k: _dec(v) for k, v in budget["actual"].items()},
            "target": {k: _dec(v) for k, v in budget["target"].items()},
            "overshoot": budget["overshoot"],
            "undershoot": budget.get("undershoot") or [],
            "window": spend_label,
        }
    elif "budget_agent" in routes and ctx["profile"]:
        # Fall back to profile expenses as uncategorised wants so the page isn't empty.
        budget = fifty_thirty_twenty(
            ctx["profile"]["monthly_income"],
            {"other": ctx["profile"]["monthly_expenses"]},
        )
        ctx["budget"] = {
            "actual": {k: _dec(v) for k, v in budget["actual"].items()},
            "target": {k: _dec(v) for k, v in budget["target"].items()},
            "overshoot": budget["overshoot"],
            "undershoot": budget.get("undershoot") or [],
            "window": "profile expenses",
        }

    if "investment_agent" in routes:
        age = int(params.get("age", 30))
        risk = str(params.get("risk_profile", "moderate"))
        alloc = risk_allocation(age, risk)
        blended = blended_expected_return(alloc)
        if params.get("expected_return") is not None and params.get("expected_return") != "":
            # UI may send percent (11) or fraction (0.11)
            raw_er = Decimal(str(params.get("expected_return")))
            er = raw_er / Decimal(100) if raw_er > 1 else raw_er
        else:
            er = blended
        default_sip = (
            ctx["profile"]["surplus"]
            if ctx.get("profile") and ctx["profile"].get("surplus") is not None
            else 10000
        )
        monthly = Decimal(str(params.get("monthly_sip", default_sip)))
        if monthly < 0:
            monthly = Decimal("0")
        starting = Decimal(str(params.get("starting_corpus", 0) or 0))
        years = int(params.get("years", 20))
        growth = project_growth(monthly, years, er, initial_corpus=starting)
        ctx["investment"] = {
            "allocation": {k: _dec(v) for k, v in alloc.items()},
            "expected_return": str(er),
            "blended_return": str(blended),
            "projected_corpus": _dec(growth),
            "monthly_sip": _dec(monthly),
            "starting_corpus": _dec(starting),
            "years": years,
            "age": age,
            "risk_profile": risk,
        }

    if "tax_agent" in routes:
        profile = ctx.get("profile") or {}
        default_gross = (
            profile["monthly_income"] * 12
            if profile.get("monthly_income") is not None
            else 1000000
        )
        gross = Decimal(str(params.get("gross_income", default_gross)))
        deductions = params.get("deductions")
        if not deductions:
            # Single "old-regime deductions" field from UI → 80C (engine caps to limit).
            old_ded = params.get("old_regime_deductions")
            if old_ded is not None and old_ded != "":
                deductions = {"80c": Decimal(str(old_ded))}
            else:
                deductions = {"80c": 150000, "80d": 25000}
        monthly_nps = Decimal(str(params.get("monthly_nps", 5000) or 0))
        if monthly_nps > 0 and "80ccd_1b" not in deductions:
            # Rough annual NPS eligible for 80CCD(1B); engine applies the YAML cap.
            deductions = {**deductions, "80ccd_1b": monthly_nps * 12}
        cmp = compare_regimes(gross, deductions)

        age = int(params.get("age", profile.get("age") or 30))
        retire_age = int(params.get("retirement_age", 60))
        years = max(1, retire_age - age)
        monthly_epf = Decimal(str(params.get("monthly_epf", 0) or 0))
        current_corpus = Decimal(str(params.get("current_corpus", 0) or 0))
        monthly_expenses = Decimal(str(params.get("monthly_expenses", 0) or 0))

        tax_cfg = load_tax_config()
        epf_rate = Decimal(str(tax_cfg["epf"]["interest_rate"]))
        # UI "Monthly EPF" is contribution (employee+employer), not basic salary base.
        if monthly_epf > 0:
            epf_corpus = project_growth(monthly_epf, years, epf_rate)
            epf_monthly_used = monthly_epf
        else:
            epf = epf_projection(50000, years)
            epf_corpus = epf["corpus"]
            epf_monthly_used = epf["monthly_contribution"]
        nps = nps_projection(monthly_nps if monthly_nps > 0 else 5000, years)
        # Grow existing corpus at a conservative 8% with no new SIP.
        grown_lump = project_growth(0, years, Decimal("0.08"), initial_corpus=current_corpus)
        retirement_corpus = _dec(grown_lump + epf_corpus + nps["corpus"])
        # Rough annual expense need at retirement (today's expenses, no inflation for now).
        annual_need = _dec(monthly_expenses * 12) if monthly_expenses > 0 else None

        ctx["tax"] = {
            "financial_year": cmp["financial_year"],
            "better_regime": cmp["better_regime"],
            "old_total_tax": _dec(cmp["old"]["total_tax"]),
            "new_total_tax": _dec(cmp["new"]["total_tax"]),
            "savings_vs_other": _dec(cmp["savings_vs_other"]),
            "gross_income": _dec(gross),
            "age": age,
            "retirement_age": retire_age,
            "years_to_retire": years,
            "monthly_expenses": _dec(monthly_expenses),
            "current_corpus": _dec(current_corpus),
            "monthly_epf": _dec(epf_monthly_used),
            "monthly_nps": _dec(nps["monthly_contribution"]),
            "sip_10y": _dec(sip_maturity(10000, 10, 0.12)),
            "epf_corpus": _dec(epf_corpus),
            "nps_corpus": _dec(nps["corpus"]),
            "retirement_corpus": retirement_corpus,
            "annual_expense_need": annual_need,
            "mode": str(params.get("mode") or "tax"),
        }

    if "debt_agent" in routes:
        debts_meta = await tools.list_debts(db, user_id)
        ctx["debts_meta"] = debts_meta
        # If caller supplies structured debts, run payoff; else note insufficient data.
        raw_debts = params.get("debts") or []
        if raw_debts:
            debts = [
                Debt(
                    name=d["name"],
                    principal=Decimal(str(d["principal"])),
                    annual_rate=Decimal(str(d["annual_rate"])),
                    min_emi=Decimal(str(d["min_emi"])),
                )
                for d in raw_debts
            ]
            extra = Decimal(str(params.get("extra_monthly", ctx["profile"]["surplus"] if ctx["profile"] else 0)))
            av = payoff_schedule(debts, extra_monthly=extra, method="avalanche")
            sn = payoff_schedule(debts, extra_monthly=extra, method="snowball")
            ctx["debt_payoff"] = {
                "avalanche_months": av["months"],
                "avalanche_interest": _dec(av["total_interest"]),
                "avalanche_payoff_date": av["payoff_date"],
                "snowball_months": sn["months"],
                "snowball_interest": _dec(sn["total_interest"]),
                "snowball_payoff_date": sn["payoff_date"],
                "extra_monthly": _dec(extra),
            }

    if "portfolio_agent" in routes:
        try:
            returns_path = config_path("sample_asset_returns.csv")
            prices = load_returns_csv(returns_path)
            opt = optimize_portfolio(prices)
            sip = Decimal(
                str(
                    params.get(
                        "monthly_sip",
                        ctx["profile"]["surplus"]
                        if ctx.get("profile") and ctx["profile"].get("surplus") is not None
                        else 10000,
                    )
                )
            )
            if sip <= 0:
                sip = Decimal("10000")
            corpus = project_growth(
                sip,
                15,
                float(opt["max_sharpe"]["expected_return"]),
            )
            ctx["portfolio"] = {
                "max_sharpe": {
                    "weights": {
                        k: f"{Decimal(str(v)):.4f}"
                        for k, v in opt["max_sharpe"]["weights"].items()
                    },
                    "expected_return": f"{Decimal(str(opt['max_sharpe']['expected_return'])):.4f}",
                    "volatility": f"{Decimal(str(opt['max_sharpe']['volatility'])):.4f}",
                    "sharpe": f"{Decimal(str(opt['max_sharpe']['sharpe'])):.4f}",
                },
                "min_volatility": {
                    "weights": {
                        k: f"{Decimal(str(v)):.4f}"
                        for k, v in opt["min_volatility"]["weights"].items()
                    },
                    "expected_return": f"{Decimal(str(opt['min_volatility']['expected_return'])):.4f}",
                    "volatility": f"{Decimal(str(opt['min_volatility']['volatility'])):.4f}",
                    "sharpe": f"{Decimal(str(opt['min_volatility']['sharpe'])):.4f}",
                },
                "frontier": [
                    {
                        "return": f"{Decimal(str(p['return'])):.4f}",
                        "volatility": f"{Decimal(str(p['volatility'])):.4f}",
                        "sharpe": f"{Decimal(str(p['sharpe'])):.4f}",
                    }
                    for p in opt.get("frontier") or []
                ],
                "monthly_sip": _dec(sip),
                "corpus_15y": _dec(corpus),
                "returns_source": "config/sample_asset_returns.csv",
            }
        except Exception as exc:
            ctx["portfolio_error"] = str(exc)

    chunks = retrieve(user_id, query, k=6)
    rag = [
        {
            "text": c.text,
            "score": c.score,
            "source_file": c.source_file,
            "page": c.page,
        }
        for c in chunks
    ]
    return ctx, rag


def _figures_from_ctx(ctx: dict[str, Any]) -> list[str]:
    figs: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, Decimal):
            figs.append(f"{obj:.2f}")
        elif isinstance(obj, bool):
            return
        elif isinstance(obj, int):
            figs.append(f"{Decimal(obj):.2f}")
        elif isinstance(obj, float):
            figs.append(f"{Decimal(str(obj)):.2f}")
        elif isinstance(obj, str):
            try:
                Decimal(obj)
                figs.append(obj if "." in obj else f"{Decimal(obj):.2f}")
            except Exception:
                pass

    walk(ctx)
    # Expand fraction weights/returns into percent forms the LLM often cites.
    expanded = list(_expand_allowed(figs))
    # unique preserve order (raw engine figs first, then expansions)
    seen = set()
    out = []
    for f in figs + expanded:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


async def run_agents(
    db: AsyncSession,
    user_id: int,
    query: str,
    *,
    params: dict[str, Any] | None = None,
    llm: LLMFn | None = None,
    force_routes: list[str] | None = None,
) -> dict[str, Any]:
    routes = force_routes or route_query(query)
    ctx, rag = await _gather_context(db, user_id, query, routes, params)
    figures = _figures_from_ctx(ctx)
    fy = load_tax_config()["financial_year"]

    agent_outputs: dict[str, dict[str, Any]] = {}
    for agent in routes:
        system = (
            f"You are the {agent} for an Indian personal finance coach (MoneyMitra). "
            "Use ONLY the provided computed figures. Do not invent rupee amounts. "
            "Return JSON with keys summary, recommendations (array of strings), "
            "figures_used (array of numeric strings you cited from the context). "
            "Never compute new numbers. "
            "Write in easy layman English for a normal salaried Indian user: short sentences, "
            "no jargon, no dense paragraphs. Prefer plain words like needs, wants, savings, "
            "EMI, SIP. Keep summary under 120 words."
        )
        if agent == "budget_agent":
            system += (
                " For budget_agent: first explain the 50/30/20 idea in one short line, "
                "then say what is high/low vs target in plain words, then end with one clear bottom line."
            )
        if agent == "investment_agent":
            system += (
                " For investment_agent: cite exact rupee amounts from Allowed figures "
                "(e.g. 9058406.48), not round lakhs. When mentioning allocation, use the "
                "percent integers from Allowed figures. Put every cited amount in figures_used."
            )
        user_msg = (
            f"User question: {query}\n\n"
            f"Computed context JSON:\n{json.dumps(ctx, default=str)[:8000]}\n\n"
            f"RAG snippets:\n{json.dumps(rag, default=str)[:3000]}\n\n"
            f"Allowed figures_used candidates: {figures[:80]}"
        )
        out = await call_agent_llm(system, user_msg, llm=llm)
        # Prefer LLM figures_used when present; always fall back to engine figures.
        allowed_set = _expand_allowed(figures)
        used = [
            f
            for f in (out.figures_used or [])
            if (_canon_amount(f) or _normalize_amount(f)) in allowed_set
            or _normalize_amount(f) in allowed_set
        ]
        if not used:
            used = figures[:40]
        out = AgentOutput(
            summary=out.summary,
            recommendations=out.recommendations,
            figures_used=used,
        )
        agent_outputs[agent] = out.model_dump()

    # Merge
    if len(agent_outputs) == 1:
        merged = AgentOutput.model_validate(next(iter(agent_outputs.values())))
    else:
        summaries = []
        recs: list[str] = []
        figs: list[str] = []
        for name, payload in agent_outputs.items():
            summaries.append(f"[{name}] {payload['summary']}")
            recs.extend(payload.get("recommendations") or [])
            figs.extend(payload.get("figures_used") or [])
        merged = AgentOutput(
            summary="\n\n".join(summaries),
            recommendations=recs,
            figures_used=list(dict.fromkeys(figs)),
        )

    guarded = apply_guardrail(
        merged,
        financial_year=fy,
        allowed_figures=figures,
    )
    return {
        "route": routes,
        "tool_results": ctx,
        "rag_chunks": rag,
        "agent_outputs": agent_outputs,
        "answer": guarded,
    }


def build_graph():
    """Expose a LangGraph StateGraph for documentation/extension (async runner uses run_agents)."""
    g = StateGraph(GraphState)

    def router_node(state: GraphState) -> GraphState:
        state["route"] = route_query(state.get("query") or "")
        return state

    g.add_node("router", router_node)
    g.set_entry_point("router")
    g.add_edge("router", END)
    return g.compile()
