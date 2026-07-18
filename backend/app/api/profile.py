"""User-entered profile preferences (Step 1 on Data & Profile)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.schemas import UserProfileIn, UserProfileOut
from app.models.user import User
from app.models.user_profile import UserProfile

router = APIRouter(prefix="/api", tags=["profile"])

_ALLOWED_RISK = frozenset({"conservative", "moderate", "aggressive"})


def _out(row: UserProfile) -> UserProfileOut:
    return UserProfileOut.model_validate(row)


@router.get("/user-profile", response_model=UserProfileOut | None)
async def get_user_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileOut | None:
    row = await db.get(UserProfile, user.id)
    if row is None:
        return None
    return _out(row)


@router.put("/user-profile", response_model=UserProfileOut)
async def put_user_profile(
    body: UserProfileIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileOut:
    risk = (body.risk_profile or "moderate").strip().lower()
    if risk not in _ALLOWED_RISK:
        raise HTTPException(
            status_code=422,
            detail="risk_profile must be conservative, moderate, or aggressive",
        )

    row = await db.get(UserProfile, user.id)
    now = datetime.now(timezone.utc)
    if row is None:
        row = UserProfile(
            user_id=user.id,
            name=(body.name or "").strip()[:255],
            age=body.age,
            city=(body.city or "").strip()[:128],
            monthly_income=body.monthly_income,
            emergency_fund=body.emergency_fund,
            risk_profile=risk,
            updated_at=now,
        )
        db.add(row)
    else:
        row.name = (body.name or "").strip()[:255]
        row.age = body.age
        row.city = (body.city or "").strip()[:128]
        row.monthly_income = body.monthly_income
        row.emergency_fund = body.emergency_fund
        row.risk_profile = risk
        row.updated_at = now

    await db.commit()
    await db.refresh(row)
    return _out(row)
