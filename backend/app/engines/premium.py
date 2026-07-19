"""Premium services: subscription detection and CIBIL-oriented credit tips."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import median
from typing import Any, Sequence

import yaml

from app.core.paths import config_dir
from app.engines.profile import TxnInput, is_emi_narration
from app.models.enums import Direction

TWOPLACES = Decimal("0.01")

_BOUNCE_RE = re.compile(
    r"(BOUNCE|DISHONOU?R|INSUFFICIENT|RETURNED|UNPAID|FAILED\s*TXN)",
    re.IGNORECASE,
)
_CC_MIN_RE = re.compile(
    r"(MIN(IMUM)?\s*DUE|CREDIT\s*CARD|CARD\s*PAYMENT)",
    re.IGNORECASE,
)


def _money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _month_key(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def load_subscription_merchants(path: Path | None = None) -> list[dict[str, Any]]:
    cfg_path = path or (config_dir() / "subscription_merchants.yaml")
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    merchants = data.get("merchants") or []
    compiled: list[dict[str, Any]] = []
    for row in merchants:
        patterns = [
            re.compile(p, re.IGNORECASE) for p in (row.get("patterns") or [])
        ]
        compiled.append({"name": row["name"], "patterns": patterns})
    return compiled


def _match_subscription(name: str, description: str, merchants: list[dict]) -> str | None:
    for merchant in merchants:
        if any(p.search(description) for p in merchant["patterns"]):
            return merchant["name"]
    return None


@dataclass(frozen=True)
class SubscriptionHit:
    name: str
    amount: Decimal
    frequency: str
    last_paid: date
    occurrences: int
    category: str


def detect_subscriptions(
    transactions: Sequence[TxnInput],
    merchants: list[dict[str, Any]] | None = None,
) -> list[SubscriptionHit]:
    """Find recurring subscription debits from statement narrations."""
    merchant_rules = merchants if merchants is not None else load_subscription_merchants()
    buckets: dict[str, list[TxnInput]] = defaultdict(list)

    for txn in transactions:
        if txn.direction != Direction.debit:
            continue
        service = _match_subscription("", txn.description, merchant_rules)
        if service:
            buckets[service].append(txn)

    hits: list[SubscriptionHit] = []
    for name, rows in buckets.items():
        rows_sorted = sorted(rows, key=lambda t: t.date)
        amounts = [t.amount for t in rows_sorted]
        typical = _money(median([float(a) for a in amounts]))
        months = {_month_key(t.date) for t in rows_sorted}
        frequency = "monthly" if len(months) >= 2 else "one-off"
        hits.append(
            SubscriptionHit(
                name=name,
                amount=typical,
                frequency=frequency,
                last_paid=rows_sorted[-1].date,
                occurrences=len(rows_sorted),
                category="entertainment"
                if name
                not in {"Jio", "Airtel", "Vi (Vodafone Idea)", "ACT Fibernet"}
                else "utilities",
            )
        )

    return sorted(hits, key=lambda h: h.amount, reverse=True)


@dataclass(frozen=True)
class CibilTip:
    title: str
    detail: str
    priority: str
    factor: str


def analyze_cibil_tips(
    profile: dict[str, Any] | None,
    transactions: Sequence[TxnInput],
    subscriptions: Sequence[SubscriptionHit] | None = None,
) -> dict[str, Any]:
    """Industry-aligned credit-health tips from bank statement signals (not a bureau score)."""
    subs = list(subscriptions or detect_subscriptions(transactions))
    tips: list[CibilTip] = []

    debits = [t for t in transactions if t.direction == Direction.debit]
    credits = [t for t in transactions if t.direction == Direction.credit]

    bounced = [t for t in debits if _BOUNCE_RE.search(t.description or "")]
    if bounced:
        tips.append(
            CibilTip(
                title="Clear bounced or failed payments immediately",
                detail=(
                    f"We found {len(bounced)} bounced/returned payment(s) in your statement. "
                    "Payment history (~35% of CIBIL weight) is the top factor — even one miss "
                    "can drop your score for months. Set up auto-debit only where balance is "
                    "comfortable and maintain a buffer before EMI dates."
                ),
                priority="high",
                factor="Payment history (35%)",
            )
        )
    else:
        tips.append(
            CibilTip(
                title="Keep your clean payment streak going",
                detail=(
                    "No bounced or dishonoured debits were detected in uploaded statements. "
                    "Continue paying EMIs, card bills, and utility dues on or before the due date "
                    "to protect the payment-history component of your CIBIL score."
                ),
                priority="medium",
                factor="Payment history (35%)",
            )
        )

    emi_rows = [t for t in debits if is_emi_narration(t.description)]
    emi_months = {_month_key(t.date) for t in emi_rows}
    if emi_rows:
        if len(emi_months) >= 2:
            tips.append(
                CibilTip(
                    title="EMI payments look consistent",
                    detail=(
                        f"Loan/EMI debits appear across {len(emi_months)} month(s). "
                        "Timely EMI repayment strengthens lender trust and credit mix (~10%). "
                        "Avoid skipping months — if stressed, talk to the lender before default."
                    ),
                    priority="medium",
                    factor="Credit mix & repayment (10%)",
                )
            )
        else:
            tips.append(
                CibilTip(
                    title="Track EMI due dates closely",
                    detail=(
                        "EMI debits were found but only in a short window. Upload more months "
                        "so we can confirm on-time patterns — lenders report missed EMIs to bureaus."
                    ),
                    priority="medium",
                    factor="Payment history (35%)",
                )
            )

    cc_rows = [t for t in debits if _CC_MIN_RE.search(t.description or "")]
    if cc_rows:
        tips.append(
            CibilTip(
                title="Pay credit card bills in full, not just minimum due",
                detail=(
                    "Credit-card payments detected. Paying only the minimum keeps utilization high "
                    "(~30% of score weight). Aim to pay the full statement balance and keep "
                    "utilization under 30% of your total card limit."
                ),
                priority="high",
                factor="Credit utilisation (30%)",
            )
        )

    income = Decimal(str((profile or {}).get("monthly_income") or 0))
    expenses = Decimal(str((profile or {}).get("monthly_expenses") or 0))
    emi_outgo = Decimal(str((profile or {}).get("emi_outgo") or 0))
    surplus = Decimal(str((profile or {}).get("surplus") or 0))

    if income > 0:
        expense_ratio = expenses / income
        if expense_ratio > Decimal("0.75"):
            tips.append(
                CibilTip(
                    title="Reduce expense-to-income ratio",
                    detail=(
                        f"Expenses are about {int(expense_ratio * 100)}% of income — high outflows "
                        "raise default risk and leave little buffer before due dates. Trim "
                        "discretionary spends and build a 1–2 month emergency fund."
                    ),
                    priority="high",
                    factor="Financial stability",
                )
            )
        elif expense_ratio > Decimal("0.55"):
            tips.append(
                CibilTip(
                    title="Moderate your monthly outflows",
                    detail=(
                        f"Expenses are roughly {int(expense_ratio * 100)}% of income. "
                        "Industry guidance suggests keeping fixed + variable spends below ~70% "
                        "so EMIs and card bills are always covered on time."
                    ),
                    priority="medium",
                    factor="Financial stability",
                )
            )

        if emi_outgo > 0:
            emi_ratio = emi_outgo / income
            if emi_ratio > Decimal("0.40"):
                tips.append(
                    CibilTip(
                        title="EMI burden is high — avoid new loans",
                        detail=(
                            f"EMI outgo is about {int(emi_ratio * 100)}% of income (ideal <40%). "
                            "Lenders may hesitate on new credit; prepay high-rate debt if surplus "
                            "allows before taking fresh loans."
                        ),
                        priority="high",
                        factor="Credit utilisation & capacity (30%)",
                    )
                )
            elif emi_ratio > Decimal("0.25"):
                tips.append(
                    CibilTip(
                        title="Keep EMI-to-income within safe limits",
                        detail=(
                            f"EMI outgo is about {int(emi_ratio * 100)}% of income. "
                            "Stay below 40% before applying for home/personal loans to keep "
                            "approval odds and scores healthy."
                        ),
                        priority="medium",
                        factor="Credit utilisation & capacity (30%)",
                    )
                )

        if surplus <= 0:
            tips.append(
                CibilTip(
                    title="Create surplus before taking new credit",
                    detail=(
                        "Monthly expenses meet or exceed income in your profile. "
                        "Negative surplus increases missed-payment risk — stabilise cash flow "
                        "before new credit cards or BNPL."
                    ),
                    priority="high",
                    factor="Financial stability",
                )
            )
        elif surplus / income >= Decimal("0.15"):
            tips.append(
                CibilTip(
                    title="Healthy surplus supports score growth",
                    detail=(
                        f"You retain about {int((surplus / income) * 100)}% surplus after expenses. "
                        "Use part of this for full bill payments and emergency savings — "
                        "both reduce future credit stress."
                    ),
                    priority="low",
                    factor="Financial stability",
                )
            )

    salary_months: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for txn in credits:
        desc = (txn.description or "").upper()
        if "SALARY" in desc or "PAYROLL" in desc:
            salary_months[_month_key(txn.date)] += txn.amount
    if len(salary_months) >= 2:
        vals = [float(v) for v in salary_months.values()]
        spread = (max(vals) - min(vals)) / max(vals) if max(vals) else 0
        if spread > 0.15:
            tips.append(
                CibilTip(
                    title="Stabilise income documentation",
                    detail=(
                        "Salary credits vary across months. Lenders prefer steady income — "
                        "keep Form 16, salary slips, and ITR handy when applying for credit."
                    ),
                    priority="medium",
                    factor="Income stability",
                )
            )
        else:
            tips.append(
                CibilTip(
                    title="Income credits look stable",
                    detail=(
                        "Salary/payroll credits are consistent across uploaded months — "
                        "this supports loan eligibility and long credit history building."
                    ),
                    priority="low",
                    factor="Income stability",
                )
            )

    sub_total = sum((s.amount for s in subs), Decimal("0"))
    if subs and income > 0 and sub_total / income > Decimal("0.05"):
        names = ", ".join(s.name for s in subs[:4])
        tips.append(
            CibilTip(
                title="Review recurring subscriptions",
                detail=(
                    f"Recurring services ({names}) total about Rs. {sub_total:,.2f}/month. "
                    "Cancelling unused OTT/telecom plans frees cash for on-time bill payments."
                ),
                priority="medium",
                factor="Financial discipline",
            )
        )

    if not tips:
        tips.append(
            CibilTip(
                title="Upload statements to unlock personalised tips",
                detail=(
                    "Add bank statements on Data & Profile so we can analyse payment patterns, "
                    "EMI discipline, and spending against industry CIBIL best practices."
                ),
                priority="medium",
                factor="Getting started",
            )
        )

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    tips.sort(key=lambda t: priority_rank.get(t.priority, 9))

    outlook = "Upload statements for a personalised outlook."
    if profile and income > 0:
        high_count = sum(1 for t in tips if t.priority == "high")
        if bounced or high_count >= 2:
            outlook = "Needs attention — focus on on-time payments and lowering EMI/expense load."
        elif high_count == 1:
            outlook = "Fair — a few improvements can strengthen your credit profile."
        else:
            outlook = "Healthy signals — maintain timely payments and low utilisation."

    return {
        "outlook": outlook,
        "disclaimer": (
            "Indicative guidance from bank statements only — not an official CIBIL score "
            "or bureau report."
        ),
        "tips": [
            {
                "title": t.title,
                "detail": t.detail,
                "priority": t.priority,
                "factor": t.factor,
            }
            for t in tips[:8]
        ],
    }


def subscription_summary(hits: Sequence[SubscriptionHit]) -> dict[str, Any]:
    monthly_total = sum(
        (h.amount for h in hits if h.frequency == "monthly"),
        Decimal("0"),
    )
    return {
        "items": [
            {
                "name": h.name,
                "amount": f"{h.amount:.2f}",
                "frequency": h.frequency,
                "last_paid": h.last_paid.isoformat(),
                "occurrences": h.occurrences,
                "category": h.category,
            }
            for h in hits
        ],
        "monthly_total": f"{monthly_total:.2f}",
        "count": len(hits),
    }
