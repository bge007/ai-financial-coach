"""Transaction list, filter, and manual recategorization."""

from __future__ import annotations

import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.ingestion.categorizer import normalize_description
from app.models.category_rule import CategoryRule
from app.models.enums import Category, Direction
from app.models.schemas import (
    RecategorizeIn,
    RecategorizeOut,
    TransactionListOut,
    TransactionOut,
)
from app.models.transaction import Transaction
from app.models.user import User

router = APIRouter(prefix="/api", tags=["transactions"])

# Manual corrections beat YAML rules (YAML tops out ~120).
MANUAL_RULE_PRIORITY = 1000


@router.get("/transactions", response_model=TransactionListOut)
async def list_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    month: str | None = Query(None, description="YYYY-MM"),
    category: Category | None = None,
    direction: Direction | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> TransactionListOut:
    filters = [Transaction.user_id == user.id]

    if month:
        try:
            year_s, month_s = month.split("-")
            year, mon = int(year_s), int(month_s)
            if not (1 <= mon <= 12):
                raise ValueError
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="month must be YYYY-MM") from exc
        start = date(year, mon, 1)
        end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
        filters.append(Transaction.date >= start)
        filters.append(Transaction.date < end)

    if category is not None:
        filters.append(Transaction.category == category)
    if direction is not None:
        filters.append(Transaction.direction == direction)
    if search:
        filters.append(Transaction.description.ilike(f"%{search}%"))

    total = await db.scalar(
        select(func.count()).select_from(Transaction).where(*filters)
    )
    result = await db.execute(
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = result.scalars().all()
    return TransactionListOut(
        items=[TransactionOut.model_validate(r) for r in rows],
        total=int(total or 0),
        page=page,
        page_size=page_size,
    )


@router.post("/transactions/{txn_id}/recategorize", response_model=RecategorizeOut)
async def recategorize_transaction(
    txn_id: int,
    body: RecategorizeIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecategorizeOut:
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == txn_id,
            Transaction.user_id == user.id,
        )
    )
    txn = result.scalar_one_or_none()
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.category = body.category

    # Persist as a highest-priority exact-match rule for this user.
    normalized = normalize_description(txn.description)
    pattern = f"^{re.escape(normalized)}$"
    rule = CategoryRule(
        user_id=user.id,
        pattern=pattern,
        category=body.category.value,
        priority=MANUAL_RULE_PRIORITY,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(txn)
    await db.refresh(rule)

    return RecategorizeOut(
        transaction=TransactionOut.model_validate(txn),
        rule_id=rule.id,
    )
