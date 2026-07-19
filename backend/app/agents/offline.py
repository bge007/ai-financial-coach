"""Rule-based agent answers when the LLM is unavailable.

All rupee figures are taken from engine context only — never invented.
"""

from __future__ import annotations

from typing import Any

from app.agents.llm import AgentOutput


def _fig(v: Any) -> str | None:
    if v is None or v == "":
        return None
    return str(v)


def build_offline_output(agent: str, ctx: dict[str, Any]) -> AgentOutput:
    profile = ctx.get("profile") or {}
    builders = {
        "budget_agent": _budget,
        "investment_agent": _investment,
        "portfolio_agent": _portfolio,
        "tax_agent": _tax,
        "debt_agent": _debt,
        "coach_agent": _coach,
    }
    fn = builders.get(agent, _coach)
    return fn(ctx, profile)


def _budget(ctx: dict[str, Any], profile: dict[str, Any]) -> AgentOutput:
    budget = ctx.get("budget") or {}
    overshoot = budget.get("overshoot") or []
    figs: list[str] = []
    for key in ("monthly_income", "monthly_expenses", "surplus"):
        if profile.get(key) is not None:
            figs.append(_fig(profile[key]))
    summary_parts = ["Here is your 50/30/20 budget check from your statement data."]
    if overshoot:
        labels_list = []
        for o in overshoot[:3]:
            if isinstance(o, dict):
                labels_list.append(str(o.get("bucket") or o.get("label") or o))
            else:
                labels_list.append(str(o))
        labels = ", ".join(labels_list)
        summary_parts.append(f"You are above target in: {labels}. Trim wants first, then review needs.")
    else:
        summary_parts.append("No major bucket overshoots vs the 50/30/20 targets right now.")
    if profile.get("surplus"):
        summary_parts.append(f"Monthly surplus is ₹{profile['surplus']}.")
        figs.append(_fig(profile["surplus"]))
    return AgentOutput(
        summary=" ".join(summary_parts),
        recommendations=[
            "Track dining and shopping for the next month",
            "Move surplus to emergency fund or SIPs after essentials are covered",
        ],
        figures_used=[f for f in figs if f],
    )


def _investment(ctx: dict[str, Any], profile: dict[str, Any]) -> AgentOutput:
    inv = ctx.get("investment") or {}
    figs: list[str] = []
    surplus = profile.get("surplus") or inv.get("monthly_sip")
    if surplus:
        figs.append(_fig(surplus))
    alloc = inv.get("allocation") or {}
    if alloc:
        alloc_txt = ", ".join(
            f"{k} {float(v) * 100:.0f}%"
            for k, v in alloc.items()
        )
    else:
        alloc_txt = "moderate mix"
    corpus = inv.get("projected_corpus")
    if corpus:
        figs.append(_fig(corpus))
    summary = (
        f"Based on your profile, monthly surplus is about ₹{surplus or '0'}. "
        f"A {inv.get('risk_profile', 'moderate')} risk mix suggests: {alloc_txt}. "
    )
    if corpus:
        summary += f"At the engine's expected return, a monthly SIP of ₹{inv.get('monthly_sip', surplus)} could grow to about ₹{corpus} over {inv.get('years', 20)} years."
    else:
        summary += "Upload a recent statement on Data & Profile for fresher numbers."
    return AgentOutput(
        summary=summary,
        recommendations=[
            "Keep 3–6 months of expenses in an emergency fund before aggressive equity",
            "Start or step up SIPs with the surplus you can sustain every month",
        ],
        figures_used=[f for f in figs if f],
    )


def _portfolio(ctx: dict[str, Any], profile: dict[str, Any]) -> AgentOutput:
    port = ctx.get("portfolio") or {}
    err = ctx.get("portfolio_error")
    if err:
        return AgentOutput(
            summary=f"Portfolio optimisation could not run: {err}",
            recommendations=["Retry after uploading statement data on Data & Profile"],
            figures_used=[],
        )
    ms = port.get("max_sharpe") or {}
    weights = ms.get("weights") or {}
    weight_txt = ", ".join(f"{k} {float(v) * 100:.0f}%" for k, v in weights.items())
    figs = [
        _fig(ms.get("sharpe")),
        _fig(port.get("corpus_15y")),
        _fig(port.get("monthly_sip")),
        _fig(profile.get("surplus")),
    ]
    return AgentOutput(
        summary=(
            f"Max-Sharpe mix on sample Indian assets: {weight_txt}. "
            f"Sharpe ratio {ms.get('sharpe', 'n/a')}. "
            f"A ₹{port.get('monthly_sip', '10000')} monthly SIP could reach about ₹{port.get('corpus_15y', '0')} in 15 years at the optimised return."
        ),
        recommendations=[
            "Rebalance once or twice a year — do not chase short-term moves",
            "Use this as a starting mix; adjust for your own risk comfort",
        ],
        figures_used=[f for f in figs if f],
    )


def _tax(ctx: dict[str, Any], profile: dict[str, Any]) -> AgentOutput:
    tax = ctx.get("tax") or {}
    figs = [
        _fig(tax.get("old_total_tax")),
        _fig(tax.get("new_total_tax")),
        _fig(tax.get("savings_vs_other")),
        _fig(tax.get("gross_income")),
    ]
    better = tax.get("better_regime") or "either regime"
    return AgentOutput(
        summary=(
            f"For FY {tax.get('financial_year', '2026-27')}, the engine favours the {better} regime "
            f"on gross income ₹{tax.get('gross_income', '0')}. "
            f"Old-regime tax about ₹{tax.get('old_total_tax', '0')} vs new-regime about ₹{tax.get('new_total_tax', '0')} "
            f"(difference ₹{tax.get('savings_vs_other', '0')})."
        ),
        recommendations=[
            "Max out 80C/80D where you actually spend (PPF, ELSS, health premium)",
            "Compare again if your salary or deductions change mid-year",
        ],
        figures_used=[f for f in figs if f],
    )


def _debt(ctx: dict[str, Any], profile: dict[str, Any]) -> AgentOutput:
    payoff = ctx.get("debt_payoff")
    figs = [
        _fig(profile.get("total_debt")),
        _fig(profile.get("emi_outgo")),
        _fig(profile.get("surplus")),
    ]
    if payoff:
        figs.extend(
            [
                _fig(payoff.get("avalanche_interest")),
                _fig(payoff.get("extra_monthly")),
            ]
        )
        summary = (
            f"With extra ₹{payoff.get('extra_monthly', '0')} per month, avalanche payoff takes "
            f"{payoff.get('avalanche_months', 'n/a')} months (interest about ₹{payoff.get('avalanche_interest', '0')}). "
            f"Snowball takes {payoff.get('snowball_months', 'n/a')} months."
        )
    else:
        debt = profile.get("total_debt") or "0"
        emi = profile.get("emi_outgo") or "0"
        surplus = profile.get("surplus") or "0"
        summary = (
            f"Your statements show total debt around ₹{debt} with EMI outgo about ₹{emi} per month. "
            f"Monthly surplus is about ₹{surplus}. "
        )
        if debt not in ("0", "0.00") and float(str(debt).replace(",", "")) > 0:
            summary += (
                "If the loan rate is high (e.g. credit card or personal loan), prepaying usually beats "
                "investing the surplus. For low-rate home loans, a balanced SIP alongside EMI is common."
            )
        else:
            summary += (
                "No outstanding loan balance was detected in your uploads — investing the surplus via "
                "SIPs is reasonable once your emergency fund is in place."
            )
    return AgentOutput(
        summary=summary,
        recommendations=[
            "List each loan with rate and balance on the Debt advisor for a precise payoff plan",
            "Keep at least one month of EMI as a buffer before aggressive prepayment",
        ],
        figures_used=[f for f in figs if f],
    )


def _coach(ctx: dict[str, Any], profile: dict[str, Any]) -> AgentOutput:
    if not profile:
        return AgentOutput(
            summary=(
                "Upload a bank statement on Data & Profile first — I can then explain income, "
                "spending, surplus, and next steps in plain language."
            ),
            recommendations=["Go to Data & Profile and upload CSV or PDF"],
            figures_used=[],
        )
    figs = [
        _fig(profile.get("monthly_income")),
        _fig(profile.get("monthly_expenses")),
        _fig(profile.get("surplus")),
    ]
    return AgentOutput(
        summary=(
            f"From your statements: monthly income about ₹{profile.get('monthly_income', '0')}, "
            f"expenses about ₹{profile.get('monthly_expenses', '0')}, "
            f"surplus about ₹{profile.get('surplus', '0')}. "
            "Ask a specific question (tax, budget, SIP, loan prepay) for a focused answer."
        ),
        recommendations=[
            "Build a 3–6 month emergency fund before taking extra risk",
            "Use the specialist advisor pages for tax, budget, and portfolio details",
        ],
        figures_used=[f for f in figs if f],
    )
