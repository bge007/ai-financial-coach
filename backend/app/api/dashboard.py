"""Dashboard and analytics view-model endpoints."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import tools
from app.core.auth import get_current_user
from app.core.db import get_db
from app.engines.budget import fifty_thirty_twenty
from app.models.enums import Direction
from app.models.transaction import Transaction
from app.models.user import User

router = APIRouter(prefix="/api", tags=["dashboard"])


def _dec(v: Decimal | None) -> str | None:
    if v is None:
        return None
    return f"{Decimal(v):.2f}"


@router.get("/dashboard")
async def dashboard(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    profile = await tools.get_profile(db, user.id)
    mom = await tools.month_over_month(db, user.id, 6)
    actions: list[str] = []
    budget = None
    spend_label = None
    if profile:
        spend_label, spend = await tools.spend_by_category_recent(db, user.id, 3)
        if not spend:
            spend = {"other": profile["monthly_expenses"]}
            spend_label = "profile expenses"
        budget = fifty_thirty_twenty(profile["monthly_income"], spend)
        # Only lifestyle overshoots warrant "reduce spend". Savings above 20%
        # is usually fine (surplus / SIPs), not something to cut.
        for o in budget["overshoot"]:
            if o["bucket"] in {"needs", "wants"}:
                actions.append(
                    f"Reduce {o['bucket']} spend — over target by ₹{o['overshoot']}"
                )
        for u in budget.get("undershoot") or []:
            if u["bucket"] == "savings":
                actions.append(
                    f"Savings are ₹{u['undershoot']} below the 20% target — "
                    "consider directing more surplus into SIPs."
                )
                break
        if profile["emi_outgo"] and profile["emi_outgo"] > 0:
            actions.append(
                f"Review EMI outgo of ₹{profile['emi_outgo']} — consider prepayment if surplus is stable."
            )
        if profile["surplus"] and profile["surplus"] > 0:
            actions.append(
                f"Deploy surplus ₹{profile['surplus']} into SIPs per your risk profile."
            )
    if not actions:
        actions.append("Upload a recent bank statement to unlock a personalised action plan.")

    return {
        "profile": (
            {
                "monthly_income": _dec(profile["monthly_income"]),
                "monthly_expenses": _dec(profile["monthly_expenses"]),
                "surplus": _dec(profile["surplus"]),
                "total_debt": _dec(profile["total_debt"]),
                "emi_outgo": _dec(profile["emi_outgo"]),
            }
            if profile
            else None
        ),
        "trends": [
            {
                "month": m["month"],
                "income": _dec(m["income"]),
                "expenses": _dec(m["expenses"]),
                "surplus": _dec(m["surplus"]),
            }
            for m in mom
        ],
        "budget": (
            {
                "actual": {k: _dec(v) for k, v in budget["actual"].items()},
                "target": {k: _dec(v) for k, v in budget["target"].items()},
                "window": spend_label,
            }
            if budget
            else None
        ),
        "actions": actions[:5],
    }


@router.get("/analytics")
async def analytics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    month: str | None = Query(None, description="YYYY-MM"),
) -> dict[str, Any]:
    mom = await tools.month_over_month(db, user.id, 12)
    months = [m["month"] for m in mom]
    selected = month or (months[-1] if months else None)
    categories: dict[str, str] = {}
    top_merchants: list[dict[str, Any]] = []
    if selected:
        spend = await tools.spend_by_category(db, user.id, selected)
        categories = {k: _dec(v) for k, v in spend.items()}

        start_y, start_m = map(int, selected.split("-"))
        from datetime import date

        start = date(start_y, start_m, 1)
        end = date(start_y + 1, 1, 1) if start_m == 12 else date(start_y, start_m + 1, 1)
        result = await db.execute(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.date >= start,
                Transaction.date < end,
                Transaction.direction == Direction.debit,
            )
        )
        counter: Counter[str] = Counter()
        amounts: dict[str, Decimal] = {}
        for txn in result.scalars().all():
            label = (txn.description or "Unknown")[:40]
            counter[label] += 1
            amounts[label] = amounts.get(label, Decimal("0")) + Decimal(txn.amount)
        top_merchants = [
            {"name": name, "count": count, "amount": _dec(amounts[name])}
            for name, count in counter.most_common(8)
        ]

    return {
        "months": months,
        "selected_month": selected,
        "month_over_month": [
            {
                "month": m["month"],
                "income": _dec(m["income"]),
                "expenses": _dec(m["expenses"]),
                "surplus": _dec(m["surplus"]),
            }
            for m in mom
        ],
        "categories": categories,
        "top_merchants": top_merchants,
    }
