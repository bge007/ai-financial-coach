"""Typed tabular tools — the ONLY way agents read financial numbers."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Category, Direction
from app.models.financial_profile import FinancialProfile
from app.models.transaction import Transaction

TWOPLACES = Decimal("0.01")


def _money(v: Decimal | float | int) -> Decimal:
    return Decimal(v).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _parse_month(month: str) -> tuple[date, date]:
    year_s, month_s = month.split("-")
    year, mon = int(year_s), int(month_s)
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end


async def get_profile(db: AsyncSession, user_id: int) -> dict[str, Any] | None:
    """Return the user's FinancialProfile fields, or None if absent."""
    profile = await db.get(FinancialProfile, user_id)
    if profile is None:
        return None
    return {
        "user_id": profile.user_id,
        "monthly_income": _money(profile.monthly_income),
        "monthly_expenses": _money(profile.monthly_expenses),
        "surplus": _money(profile.surplus),
        "total_debt": _money(profile.total_debt),
        "emi_outgo": _money(profile.emi_outgo),
        "computed_at": profile.computed_at.isoformat() if profile.computed_at else None,
    }


async def monthly_summary(
    db: AsyncSession, user_id: int, month: str
) -> dict[str, Decimal]:
    """Income, expenses, and surplus for YYYY-MM (credits − debits)."""
    start, end = _parse_month(month)
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
        )
    )
    income = Decimal("0")
    expenses = Decimal("0")
    for txn in result.scalars().all():
        amt = _money(txn.amount)
        if txn.direction == Direction.credit:
            income += amt
        else:
            expenses += amt
    return {
        "income": _money(income),
        "expenses": _money(expenses),
        "surplus": _money(income - expenses),
    }


async def spend_by_category(
    db: AsyncSession, user_id: int, month: str
) -> dict[str, Decimal]:
    """Debit totals keyed by category for YYYY-MM."""
    start, end = _parse_month(month)
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.direction == Direction.debit,
        )
    )
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for txn in result.scalars().all():
        key = (
            txn.category.value
            if isinstance(txn.category, Category)
            else (txn.category or Category.other.value)
        )
        totals[key] += _money(txn.amount)
    return {k: _money(v) for k, v in sorted(totals.items())}


async def month_over_month(
    db: AsyncSession, user_id: int, n_months: int = 6
) -> list[dict[str, Any]]:
    """Last n_months of income/expense/surplus, oldest first."""
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    )
    rows = list(result.scalars().all())
    if not rows:
        return []

    by_month: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"income": Decimal("0"), "expenses": Decimal("0")}
    )
    for txn in rows:
        key = f"{txn.date.year:04d}-{txn.date.month:02d}"
        amt = _money(txn.amount)
        if txn.direction == Direction.credit:
            by_month[key]["income"] += amt
        else:
            by_month[key]["expenses"] += amt

    keys = sorted(by_month.keys())[-n_months:]
    out = []
    for key in keys:
        inc = _money(by_month[key]["income"])
        exp = _money(by_month[key]["expenses"])
        out.append(
            {
                "month": key,
                "income": inc,
                "expenses": exp,
                "surplus": _money(inc - exp),
            }
        )
    return out


async def list_debts(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    """Known debts. Statements lack principal/rate — return insufficient-data note.

    When EMI narrations exist, surface emi amounts only with outstanding=None.
    """
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.direction == Direction.debit,
        )
    )
    emi_amounts: dict[str, Decimal] = {}
    for txn in result.scalars().all():
        desc = (txn.description or "").upper()
        is_emi = (
            (isinstance(txn.category, Category) and txn.category == Category.emi)
            or bool(re.search(r"\bEMI\b|LOAN", desc))
        )
        if not is_emi:
            continue
        # Group by a coarse name token.
        name = "EMI"
        if "HDFC" in desc:
            name = "HDFC Loan EMI"
        elif "SBI" in desc:
            name = "SBI Loan EMI"
        emi_amounts[name] = _money(txn.amount)

    if not emi_amounts:
        return []

    return [
        {
            "name": name,
            "outstanding": None,
            "rate": None,
            "emi": emi,
            "note": "insufficient_data: statements do not expose outstanding principal or rate",
        }
        for name, emi in sorted(emi_amounts.items())
    ]


async def recurring_payments(db: AsyncSession, user_id: int) -> list[dict[str, Any]]:
    """Debits with the same amount appearing in ≥2 distinct months."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.direction == Direction.debit,
        )
    )
    # key: (normalized desc prefix, amount) → months
    groups: dict[tuple[str, Decimal], set[str]] = defaultdict(set)
    samples: dict[tuple[str, Decimal], str] = {}
    for txn in result.scalars().all():
        amt = _money(txn.amount)
        # Use first 24 chars of upper description as identity.
        label = re.sub(r"\s+", " ", (txn.description or "").upper()).strip()[:24]
        key = (label, amt)
        month = f"{txn.date.year:04d}-{txn.date.month:02d}"
        groups[key].add(month)
        samples[key] = txn.description

    out = []
    for (label, amt), months in groups.items():
        if len(months) >= 2:
            out.append(
                {
                    "description": samples[(label, amt)],
                    "amount": amt,
                    "months": sorted(months),
                    "occurrences": len(months),
                }
            )
    out.sort(key=lambda r: (-r["occurrences"], -r["amount"]))
    return out
