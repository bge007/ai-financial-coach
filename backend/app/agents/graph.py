"""LangGraph multi-agent orchestration."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.guardrails import apply_guardrail
from app.agents.llm import AgentOutput, LLMFn, call_agent_llm
from app.agents.router import route_query
from app.agents import tools
from app.engines.budget import fifty_thirty_twenty
from app.engines.debt import Debt, payoff_schedule
from app.engines.investment import blended_expected_return, project_growth, risk_allocation
from app.engines.tax_india import compare_regimes, epf_projection, load_tax_config, nps_projection, sip_maturity
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
    if mom:
        latest = mom[-1]["month"]
        spend = await tools.spend_by_category(db, user_id, latest)
        ctx["spend_by_category"] = {k: _dec(v) for k, v in spend.items()}
        if "budget_agent" in routes and ctx["profile"]:
            budget = fifty_thirty_twenty(ctx["profile"]["monthly_income"], spend)
            ctx["budget"] = {
                "actual": {k: _dec(v) for k, v in budget["actual"].items()},
                "target": {k: _dec(v) for k, v in budget["target"].items()},
                "overshoot": budget["overshoot"],
            }

    if "investment_agent" in routes:
        age = int(params.get("age", 30))
        risk = str(params.get("risk_profile", "moderate"))
        alloc = risk_allocation(age, risk)
        er = blended_expected_return(alloc)
        default_sip = (
            ctx["profile"]["surplus"]
            if ctx.get("profile") and ctx["profile"].get("surplus") is not None
            else 10000
        )
        monthly = Decimal(str(params.get("monthly_sip", default_sip)))
        growth = project_growth(monthly, int(params.get("years", 20)), er)
        ctx["investment"] = {
            "allocation": {k: _dec(v) for k, v in alloc.items()},
            "expected_return": str(er),
            "projected_corpus": _dec(growth),
            "monthly_sip": _dec(monthly),
            "years": int(params.get("years", 20)),
        }

    if "tax_agent" in routes:
        gross = Decimal(str(params.get("gross_income", ctx["profile"]["monthly_income"] * 12 if ctx["profile"] else 1000000)))
        deductions = params.get("deductions") or {"80c": 150000, "80d": 25000}
        cmp = compare_regimes(gross, deductions)
        ctx["tax"] = {
            "financial_year": cmp["financial_year"],
            "better_regime": cmp["better_regime"],
            "old_total_tax": _dec(cmp["old"]["total_tax"]),
            "new_total_tax": _dec(cmp["new"]["total_tax"]),
            "savings_vs_other": _dec(cmp["savings_vs_other"]),
            "sip_10y": _dec(sip_maturity(10000, 10, 0.12)),
            "epf_corpus": _dec(epf_projection(50000, 10)["corpus"]),
            "nps_corpus": _dec(nps_projection(5000, 10)["corpus"]),
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
        elif isinstance(obj, str):
            try:
                Decimal(obj)
                figs.append(obj if "." in obj else f"{Decimal(obj):.2f}")
            except Exception:
                pass

    walk(ctx)
    # unique preserve order
    seen = set()
    out = []
    for f in figs:
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
            f"You are the {agent} for an Indian personal finance coach. "
            "Use ONLY the provided computed figures. Do not invent rupee amounts. "
            "Return JSON with keys summary, recommendations (array of strings), "
            "figures_used (array of numeric strings you cited from the context). "
            "Never compute new numbers."
        )
        user_msg = (
            f"User question: {query}\n\n"
            f"Computed context JSON:\n{json.dumps(ctx, default=str)[:8000]}\n\n"
            f"RAG snippets:\n{json.dumps(rag, default=str)[:3000]}\n\n"
            f"Allowed figures_used candidates: {figures[:80]}"
        )
        out = await call_agent_llm(system, user_msg, llm=llm)
        # Ensure figures_used ⊆ context figures when possible
        if not out.figures_used:
            out = AgentOutput(
                summary=out.summary,
                recommendations=out.recommendations,
                figures_used=figures[:20],
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

    guarded = apply_guardrail(merged, financial_year=fy)
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
