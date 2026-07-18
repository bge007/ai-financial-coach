"""Dashboard and analytics view-model endpoints."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
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
    month: str | None = Query(None, description="YYYY-MM or 'all'"),
) -> dict[str, Any]:
    mom = await tools.month_over_month(db, user.id, 24)
    months = [m["month"] for m in mom]
    want_all = (month or "").lower() in {"", "all"}
    # Default landing view = All (full history). Specific month filters when chosen.
    if want_all:
        selected = "all"
    else:
        if month not in months:
            raise HTTPException(status_code=400, detail=f"Unknown month '{month}'")
        selected = month

    categories: dict[str, str] = {}
    top_merchants: list[dict[str, Any]] = []
    selected_summary: dict[str, str] | None = None

    from datetime import date

    if selected == "all":
        result = await db.execute(
            select(Transaction).where(
                Transaction.user_id == user.id,
                Transaction.direction == Direction.debit,
            )
        )
        debit_rows = list(result.scalars().all())
        # Category totals across all months.
        cat_totals: dict[str, Decimal] = {}
        for txn in debit_rows:
            cat = txn.category
            key = cat.value if hasattr(cat, "value") else str(cat or "other")
            cat_totals[key] = cat_totals.get(key, Decimal("0")) + Decimal(txn.amount)
        categories = {k: _dec(v) for k, v in sorted(cat_totals.items())}

        income = sum((Decimal(m["income"]) for m in mom), Decimal("0"))
        expenses = sum((Decimal(m["expenses"]) for m in mom), Decimal("0"))
        selected_summary = {
            "income": _dec(income),
            "expenses": _dec(expenses),
            "surplus": _dec(income - expenses),
            "label": "All months",
        }
        top_merchants = _top_merchants_from_rows(debit_rows)
    else:
        spend = await tools.spend_by_category(db, user.id, selected)
        categories = {k: _dec(v) for k, v in spend.items()}
        start_y, start_m = map(int, selected.split("-"))
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
        debit_rows = list(result.scalars().all())
        top_merchants = _top_merchants_from_rows(debit_rows)
        month_row = next((m for m in mom if m["month"] == selected), None)
        if month_row:
            selected_summary = {
                "income": _dec(month_row["income"]),
                "expenses": _dec(month_row["expenses"]),
                "surplus": _dec(month_row["surplus"]),
                "label": selected,
            }

    return {
        "months": months,
        "selected_month": selected,
        "selected_summary": selected_summary,
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


def _top_merchants_from_rows(rows: list) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    amounts: dict[str, Decimal] = {}
    for txn in rows:
        label = _merchant_label(txn.description)
        counts[label] += 1
        amounts[label] = amounts.get(label, Decimal("0")) + Decimal(txn.amount)
    ranked = sorted(amounts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return [
        {
            "name": name,
            "count": int(counts[name]),
            "amount": _dec(amount),
        }
        for name, amount in ranked
    ]


def _merchant_label(description: str | None) -> str:
    """Normalize noisy bank narrations into a readable merchant key."""
    import re

    raw = (description or "Unknown").strip()
    if not raw:
        return "Unknown"
    # Prefer ICICI-style short label before the pipe.
    if "|" in raw:
        raw = raw.split("|", 1)[0].strip() or raw
    # UPI/payee@handle → payee
    m = re.search(r"UPI/([^/\s@]+)", raw, flags=re.IGNORECASE)
    if m:
        raw = m.group(1)
    # Collapse whitespace / truncate
    raw = re.sub(r"\s+", " ", raw).strip()
    return (raw[:48] or "Unknown")
