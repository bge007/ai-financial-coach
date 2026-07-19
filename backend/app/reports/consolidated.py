"""Build consolidated report sections for all MoneyMitra modules."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import _gather_context
from app.agents.offline import build_offline_output
from app.agents import tools
from app.api.dashboard import _top_merchants_from_rows
from app.engines.budget import fifty_thirty_twenty
from app.engines.investment import project_growth
from app.models.enums import Direction
from app.models.transaction import Transaction
from app.models.user import User
from app.models.user_profile import UserProfile
from app.reports import charts


def _rs(amount: Any) -> str:
    if amount is None or amount == "":
        return "Rs. 0"
    try:
        num = Decimal(str(amount))
    except Exception:
        return str(amount)
    return f"Rs. {num:,.2f}"


def _num(amount: Any) -> float:
    try:
        return float(Decimal(str(amount or 0)))
    except Exception:
        return 0.0


def _summary_lines(text: str, max_lines: int = 3) -> list[str]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ["No data available for this section yet."]
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", cleaned) if p.strip()]
    if not parts:
        return [cleaned[:220]]
    return parts[:max_lines]


def _section(
    title: str,
    summary: str,
    bullets: list[str] | None = None,
    *,
    metrics: list[dict[str, str]] | None = None,
    tables: list[dict[str, Any]] | None = None,
    chart_images: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "summary_lines": _summary_lines(summary),
        "bullets": bullets or [],
        "metrics": metrics or [],
        "tables": tables or [],
        "charts": chart_images or [],
    }


def _month_label(month_key: str, *, short: bool = True) -> str:
    match = re.match(r"^(\d{4})-(\d{2})$", str(month_key or "").strip())
    if not match:
        return str(month_key)
    year, month = int(match.group(1)), int(match.group(2))
    names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    if short:
        return f"{names[month - 1]} {str(year)[2:]}"
    return f"{names[month - 1]} {year}"


def _truncate(text: str, limit: int = 42) -> str:
    raw = " ".join((text or "").split())
    return raw if len(raw) <= limit else raw[: limit - 1] + "…"


def _dashboard_actions(profile: dict[str, Any] | None, budget: dict[str, Any] | None) -> list[str]:
    actions: list[str] = []
    if profile and budget:
        for o in budget.get("overshoot") or []:
            if o.get("bucket") in {"needs", "wants"}:
                actions.append(f"Reduce {o['bucket']} spend — over target by Rs. {o['overshoot']}")
        for u in budget.get("undershoot") or []:
            if u.get("bucket") == "savings":
                actions.append(
                    f"Savings are Rs. {u['undershoot']} below the 20% target — "
                    "consider directing more surplus into SIPs."
                )
                break
        if profile.get("emi_outgo") and Decimal(str(profile["emi_outgo"])) > 0:
            actions.append(
                f"Review EMI outgo of Rs. {profile['emi_outgo']} — "
                "consider prepayment if surplus is stable."
            )
        if profile.get("surplus") and Decimal(str(profile["surplus"])) > 0:
            actions.append(
                f"Deploy surplus Rs. {profile['surplus']} into SIPs per your risk profile."
            )
    if not actions:
        actions.append("Upload a recent bank statement to unlock a personalised action plan.")
    return actions[:5]


async def build_consolidated_sections(
    db: AsyncSession,
    user: User,
    user_profile: UserProfile | None,
) -> dict[str, Any]:
    profile = await tools.get_profile(db, user.id)
    mom_12 = await tools.month_over_month(db, user.id, 12)
    mom_24 = await tools.month_over_month(db, user.id, 24)

    spend_label, spend = (None, {})
    budget_raw = None
    if profile:
        spend_label, spend = await tools.spend_by_category_recent(db, user.id, 3)
        if not spend:
            spend = {"other": profile["monthly_expenses"]}
            spend_label = "profile expenses"
        budget_raw = fifty_thirty_twenty(profile["monthly_income"], spend)

    sections: list[dict[str, Any]] = []

    # --- Dashboard ---
    dash_lines: list[str] = []
    dash_metrics: list[dict[str, str]] = []
    dash_charts: list[dict[str, Any]] = []
    dash_tables: list[dict[str, Any]] = []
    if profile:
        dash_lines.append(
            f"Monthly income {_rs(profile['monthly_income'])}, expenses "
            f"{_rs(profile['monthly_expenses'])}, surplus {_rs(profile['surplus'])}."
        )
        dash_metrics = [
            {"label": "Monthly income", "value": _rs(profile["monthly_income"])},
            {"label": "Monthly expenses", "value": _rs(profile["monthly_expenses"])},
            {"label": "Surplus", "value": _rs(profile["surplus"])},
            {"label": "EMI outgo", "value": _rs(profile.get("emi_outgo"))},
            {"label": "Total debt", "value": _rs(profile.get("total_debt"))},
        ]
        if mom_12:
            labels = [_month_label(m["month"]) for m in mom_12]
            dash_charts.append(
                {
                    "title": "Income vs expenses (last 12 months)",
                    "png": charts.chart_income_expense_trend(
                        labels,
                        [_num(m["income"]) for m in mom_12],
                        [_num(m["expenses"]) for m in mom_12],
                        title="Dashboard — income vs expenses",
                    ),
                }
            )
        if budget_raw:
            overs = [
                o["bucket"]
                for o in budget_raw.get("overshoot") or []
                if o["bucket"] in {"needs", "wants"}
            ]
            if overs:
                dash_lines.append(
                    f"50/30/20 check: overspending in {', '.join(overs)} ({spend_label})."
                )
            else:
                dash_lines.append("50/30/20 buckets look broadly on track for recent months.")
        actions = _dashboard_actions(profile, budget_raw)
        dash_tables.append(
            {
                "title": "Coach action plan",
                "headers": ["#", "Action"],
                "rows": [[str(i), a] for i, a in enumerate(actions, start=1)],
            }
        )
    else:
        dash_lines.append("Upload a bank statement on Data & Profile to populate your dashboard.")

    sections.append(
        {
            "title": "Dashboard",
            "summary_lines": dash_lines[:3],
            "bullets": [],
            "metrics": dash_metrics,
            "tables": dash_tables,
            "charts": dash_charts,
        }
    )

    # --- Data & Profile ---
    dp_lines: list[str] = []
    dp_tables: list[dict[str, Any]] = []
    if user_profile or profile:
        if user_profile:
            dp_lines.append(
                f"Profile: {user_profile.name or user.name}, age {user_profile.age or '-'}, "
                f"{user_profile.city or '-'}, risk {user_profile.risk_profile}."
            )
            dp_tables.append(
                {
                    "title": "Declared profile",
                    "headers": ["Field", "Value"],
                    "rows": [
                        ["Name", user_profile.name or user.name or "-"],
                        ["Age", str(user_profile.age or "-")],
                        ["City", user_profile.city or "-"],
                        ["Monthly income (declared)", _rs(user_profile.monthly_income)],
                        ["Emergency fund", _rs(user_profile.emergency_fund)],
                        ["Risk profile", str(user_profile.risk_profile or "-")],
                    ],
                }
            )
        if profile:
            dp_lines.append(
                f"Computed from statements — income {_rs(profile['monthly_income'])}, "
                f"expenses {_rs(profile['monthly_expenses'])}, surplus {_rs(profile['surplus'])}."
            )
            dp_tables.append(
                {
                    "title": "Computed from statements",
                    "headers": ["Metric", "Value"],
                    "rows": [
                        ["Monthly income", _rs(profile["monthly_income"])],
                        ["Monthly expenses", _rs(profile["monthly_expenses"])],
                        ["Surplus", _rs(profile["surplus"])],
                        ["EMI outgo", _rs(profile.get("emi_outgo"))],
                        ["Total debt", _rs(profile.get("total_debt"))],
                    ],
                }
            )
        if user_profile and user_profile.emergency_fund is not None:
            dp_lines.append(f"Declared emergency fund: {_rs(user_profile.emergency_fund)}.")
    else:
        dp_lines = [
            "Add your personal details and upload a CSV or PDF bank statement to unlock computed metrics."
        ]

    sections.append(
        {
            "title": "Data & Profile",
            "summary_lines": dp_lines[:3],
            "bullets": [],
            "metrics": [],
            "tables": dp_tables,
            "charts": [],
        }
    )

    # --- Transactions ---
    txn_stats = await db.execute(
        select(
            func.count(Transaction.id),
            func.min(Transaction.date),
            func.max(Transaction.date),
        ).where(Transaction.user_id == user.id)
    )
    count, min_d, max_d = txn_stats.one()
    txn_tables: list[dict[str, Any]] = []
    if count:
        recent = (
            await db.execute(
                select(Transaction)
                .where(Transaction.user_id == user.id)
                .order_by(Transaction.date.desc(), Transaction.id.desc())
                .limit(20)
            )
        ).scalars().all()
        txn_tables.append(
            {
                "title": "Recent transactions (latest 20)",
                "headers": ["Date", "Description", "Dir.", "Amount", "Category"],
                "rows": [
                    [
                        str(t.date),
                        _truncate(t.description, 36),
                        t.direction.value if hasattr(t.direction, "value") else str(t.direction),
                        _rs(t.amount),
                        t.category.value if hasattr(t.category, "value") else str(t.category or "-"),
                    ]
                    for t in recent
                ],
            }
        )
        sections.append(
            {
                "title": "Transactions",
                "summary_lines": [
                    f"{int(count)} transactions parsed from your uploaded statements.",
                    f"Date range: {min_d} to {max_d}." if min_d and max_d else "Date range available in the app.",
                    "Categories are assigned via rules with optional AI fallback for uncategorised rows.",
                ],
                "bullets": [],
                "metrics": [{"label": "Total transactions", "value": str(int(count))}],
                "tables": txn_tables,
                "charts": [],
            }
        )
    else:
        sections.append(
            _section(
                "Transactions",
                "No transactions yet. Upload a statement to see categorised debits and credits.",
            )
        )

    # --- Analytics ---
    if profile and mom_24:
        debit_rows = (
            await db.execute(
                select(Transaction).where(
                    Transaction.user_id == user.id,
                    Transaction.direction == Direction.debit,
                )
            )
        ).scalars().all()
        cat_totals: dict[str, Decimal] = {}
        for txn in debit_rows:
            cat = txn.category
            key = cat.value if hasattr(cat, "value") else str(cat or "other")
            cat_totals[key] = cat_totals.get(key, Decimal("0")) + Decimal(txn.amount)
        top_cats = sorted(cat_totals.items(), key=lambda kv: kv[1], reverse=True)[:8]
        cat_txt = ", ".join(f"{k} {_rs(v)}" for k, v in top_cats[:3]) if top_cats else "none"
        income_total = sum((Decimal(str(m["income"])) for m in mom_24), Decimal("0"))
        expense_total = sum((Decimal(str(m["expenses"])) for m in mom_24), Decimal("0"))
        merchants = _top_merchants_from_rows(list(debit_rows))

        analytics_charts: list[dict[str, Any]] = []
        mom_slice = mom_24[-12:]
        analytics_charts.append(
            {
                "title": "Income vs expenses trend",
                "png": charts.chart_income_expense_trend(
                    [_month_label(m["month"]) for m in mom_slice],
                    [_num(m["income"]) for m in mom_slice],
                    [_num(m["expenses"]) for m in mom_slice],
                    title="Analytics — month-over-month",
                ),
            }
        )
        if top_cats:
            analytics_charts.append(
                {
                    "title": "Spend by category",
                    "png": charts.chart_horizontal_bar(
                        [k.replace("_", " ") for k, _ in top_cats],
                        [_num(v) for _, v in top_cats],
                        title="Top spending categories (all time)",
                    ),
                }
            )

        sections.append(
            {
                "title": "Analytics",
                "summary_lines": [
                    f"Top spend categories (all time): {cat_txt}.",
                    f"Tracking {len(mom_24)} month(s) of income vs expense trends.",
                    "Category mix and top merchants are detailed below.",
                ],
                "bullets": [],
                "metrics": [
                    {"label": "Total income", "value": _rs(income_total)},
                    {"label": "Total expenses", "value": _rs(expense_total)},
                    {"label": "Net surplus", "value": _rs(income_total - expense_total)},
                ],
                "tables": [
                    {
                        "title": "Top merchants",
                        "headers": ["Merchant", "Txns", "Amount"],
                        "rows": [
                            [m["name"], str(m["count"]), _rs(m["amount"])]
                            for m in merchants[:10]
                        ],
                    }
                ],
                "charts": analytics_charts,
            }
        )
    else:
        sections.append(
            _section(
                "Analytics",
                "Analytics unlock after statement upload — month-over-month trends and category breakdown.",
            )
        )

    # --- Advisor modules (engines + offline summaries) ---
    params: dict[str, Any] = {}
    if user_profile:
        params["age"] = user_profile.age or 30
        params["risk_profile"] = user_profile.risk_profile or "moderate"
        if user_profile.monthly_income is not None:
            params["gross_income"] = float(user_profile.monthly_income) * 12
        if user_profile.monthly_income is not None:
            params["monthly_expenses"] = float(
                profile["monthly_expenses"] if profile else user_profile.monthly_income * Decimal("0.6")
            )

    ctx, _ = await _gather_context(
        db,
        user.id,
        "Consolidated financial report",
        [
            "budget_agent",
            "investment_agent",
            "portfolio_agent",
            "tax_agent",
            "coach_agent",
        ],
        params,
    )

    # --- Budget Advisor ---
    budget_ctx = ctx.get("budget") or {}
    budget_out = build_offline_output("budget_agent", ctx)
    budget_metrics: list[dict[str, str]] = []
    budget_charts: list[dict[str, Any]] = []
    budget_tables: list[dict[str, Any]] = []
    if budget_ctx:
        actual = budget_ctx.get("actual") or {}
        target = budget_ctx.get("target") or {}
        buckets = ["needs", "wants", "savings"]
        budget_metrics = [
            {"label": f"{b.title()} (actual)", "value": _rs(actual.get(b))}
            for b in buckets
        ]
        budget_charts.append(
            {
                "title": "50/30/20 actual vs target",
                "png": charts.chart_grouped_bar(
                    buckets,
                    {
                        "Actual": [_num(actual.get(b)) for b in buckets],
                        "Target": [_num(target.get(b)) for b in buckets],
                    },
                    title=f"Budget — actual vs target ({budget_ctx.get('window', 'recent')})",
                ),
            }
        )
        budget_tables.append(
            {
                "title": "Bucket comparison",
                "headers": ["Bucket", "Actual", "Target", "Gap"],
                "rows": [
                    [
                        b.title(),
                        _rs(actual.get(b)),
                        _rs(target.get(b)),
                        _rs(_num(actual.get(b)) - _num(target.get(b))),
                    ]
                    for b in buckets
                ],
            }
        )
    sections.append(
        {
            "title": "Budget Advisor",
            "summary_lines": _summary_lines(budget_out.summary),
            "bullets": (budget_out.recommendations or [])[:5],
            "metrics": budget_metrics,
            "tables": budget_tables,
            "charts": budget_charts,
        }
    )

    # --- Investment Advisor ---
    inv = ctx.get("investment") or {}
    inv_out = build_offline_output("investment_agent", ctx)
    inv_metrics: list[dict[str, str]] = []
    inv_charts: list[dict[str, Any]] = []
    inv_tables: list[dict[str, Any]] = []
    if inv:
        inv_metrics = [
            {"label": "Projected corpus", "value": _rs(inv.get("projected_corpus"))},
            {"label": "Expected return", "value": f"{_num(inv.get('expected_return')) * 100:.1f}%"},
            {"label": "Blended return", "value": f"{_num(inv.get('blended_return')) * 100:.1f}%"},
        ]
        alloc = inv.get("allocation") or {}
        if alloc:
            labels = list(alloc.keys())
            inv_charts.append(
                {
                    "title": "Asset allocation",
                    "png": charts.chart_pie(
                        labels,
                        [_num(alloc[k]) for k in labels],
                        title=f"Investment mix ({inv.get('risk_profile', 'moderate')})",
                    ),
                }
            )
        years = int(inv.get("years") or 20)
        monthly = Decimal(str(inv.get("monthly_sip") or 0))
        starting = Decimal(str(inv.get("starting_corpus") or 0))
        er = Decimal(str(inv.get("expected_return") or 0))
        growth_years = list(range(0, years + 1, max(1, years // 10)))
        if growth_years[-1] != years:
            growth_years.append(years)
        growth_vals = [
            float(project_growth(monthly, y, er, initial_corpus=starting))
            for y in growth_years
        ]
        inv_charts.append(
            {
                "title": "Wealth projection",
                "png": charts.chart_line(
                    [str(y) for y in growth_years],
                    {"Corpus": growth_vals},
                    title="Investment growth path",
                    xlabel="Years",
                ),
            }
        )
        inv_tables.append(
            {
                "title": "Assumptions",
                "headers": ["Parameter", "Value"],
                "rows": [
                    ["Monthly SIP", _rs(inv.get("monthly_sip"))],
                    ["Starting corpus", _rs(inv.get("starting_corpus"))],
                    ["Horizon (years)", str(inv.get("years", "-"))],
                    ["Age", str(inv.get("age", "-"))],
                    ["Risk profile", str(inv.get("risk_profile", "-"))],
                ],
            }
        )
    sections.append(
        {
            "title": "Investment Advisor",
            "summary_lines": _summary_lines(inv_out.summary),
            "bullets": (inv_out.recommendations or [])[:5],
            "metrics": inv_metrics,
            "tables": inv_tables,
            "charts": inv_charts,
        }
    )

    # --- Portfolio Optimizer ---
    port = ctx.get("portfolio") or {}
    port_out = build_offline_output("portfolio_agent", ctx)
    port_metrics: list[dict[str, str]] = []
    port_charts: list[dict[str, Any]] = []
    port_tables: list[dict[str, Any]] = []
    if port:
        ms = port.get("max_sharpe") or {}
        mv = port.get("min_volatility") or {}
        port_metrics = [
            {"label": "Max Sharpe ratio", "value": str(ms.get("sharpe", "-"))},
            {"label": "Max Sharpe return", "value": f"{_num(ms.get('expected_return')) * 100:.1f}%"},
            {"label": "Max Sharpe volatility", "value": f"{_num(ms.get('volatility')) * 100:.1f}%"},
            {"label": "15Y corpus @ SIP", "value": _rs(port.get("corpus_15y"))},
        ]
        weights = ms.get("weights") or {}
        if weights:
            wl = list(weights.keys())
            port_charts.append(
                {
                    "title": "Max-Sharpe allocation",
                    "png": charts.chart_pie(
                        wl,
                        [_num(weights[k]) for k in wl],
                        title="Portfolio — max Sharpe weights",
                    ),
                }
            )
        frontier = port.get("frontier") or []
        if frontier:
            vols = [_num(p["volatility"]) for p in frontier]
            rets = [_num(p["return"]) for p in frontier]
            highlight = (_num(ms.get("volatility")), _num(ms.get("expected_return")))
            port_charts.append(
                {
                    "title": "Efficient frontier",
                    "png": charts.chart_scatter_line(
                        vols,
                        rets,
                        title="Efficient frontier (sample)",
                        highlight=highlight if ms else None,
                    ),
                }
            )
        port_tables.append(
            {
                "title": "Portfolio comparison",
                "headers": ["Portfolio", "Return", "Volatility", "Sharpe"],
                "rows": [
                    [
                        "Max Sharpe",
                        f"{_num(ms.get('expected_return')) * 100:.1f}%",
                        f"{_num(ms.get('volatility')) * 100:.1f}%",
                        str(ms.get("sharpe", "-")),
                    ],
                    [
                        "Min volatility",
                        f"{_num(mv.get('expected_return')) * 100:.1f}%",
                        f"{_num(mv.get('volatility')) * 100:.1f}%",
                        str(mv.get("sharpe", "-")),
                    ],
                ],
            }
        )
    sections.append(
        {
            "title": "Portfolio Optimizer",
            "summary_lines": _summary_lines(port_out.summary),
            "bullets": (port_out.recommendations or [])[:5],
            "metrics": port_metrics,
            "tables": port_tables,
            "charts": port_charts,
        }
    )

    # --- Tax & Retirement ---
    tax = ctx.get("tax") or {}
    tax_out = build_offline_output("tax_agent", ctx)
    tax_metrics: list[dict[str, str]] = []
    tax_charts: list[dict[str, Any]] = []
    tax_tables: list[dict[str, Any]] = []
    if tax:
        tax_metrics = [
            {"label": "Old regime tax", "value": _rs(tax.get("old_total_tax"))},
            {"label": "New regime tax", "value": _rs(tax.get("new_total_tax"))},
            {"label": "Better regime", "value": str(tax.get("better_regime", "-")).title()},
            {"label": "Tax savings", "value": _rs(tax.get("savings_vs_other"))},
            {"label": "Retirement corpus", "value": _rs(tax.get("retirement_corpus"))},
        ]
        tax_charts.append(
            {
                "title": "Tax regime comparison",
                "png": charts.chart_tax_comparison(
                    _num(tax.get("old_total_tax")),
                    _num(tax.get("new_total_tax")),
                    title=f"Tax comparison — FY {tax.get('financial_year', '')}",
                ),
            }
        )
        tax_tables.append(
            {
                "title": "Retirement projection",
                "headers": ["Component", "Value"],
                "rows": [
                    ["Years to retire", str(tax.get("years_to_retire", "-"))],
                    ["EPF corpus (projected)", _rs(tax.get("epf_corpus"))],
                    ["NPS corpus (projected)", _rs(tax.get("nps_corpus"))],
                    ["Total retirement corpus", _rs(tax.get("retirement_corpus"))],
                    ["Annual expense need", _rs(tax.get("annual_expense_need"))],
                ],
            }
        )
    sections.append(
        {
            "title": "Tax & Retirement",
            "summary_lines": _summary_lines(tax_out.summary),
            "bullets": (tax_out.recommendations or [])[:5],
            "metrics": tax_metrics,
            "tables": tax_tables,
            "charts": tax_charts,
        }
    )

    # --- Ask the Coach ---
    coach_out = build_offline_output("coach_agent", ctx)
    sections.append(
        {
            "title": "Ask the Coach",
            "summary_lines": _summary_lines(coach_out.summary),
            "bullets": (coach_out.recommendations or [])[:5],
            "metrics": [],
            "tables": [],
            "charts": [],
        }
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_name": user.name or user.email,
        "user_email": user.email,
        "sections": sections,
    }
