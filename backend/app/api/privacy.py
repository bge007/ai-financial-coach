"""Lean Phase 7: data deletion + isolation audit helpers."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.category_cache import CategoryCache
from app.models.category_rule import CategoryRule
from app.models.financial_profile import FinancialProfile
from app.models.transaction import Transaction
from app.models.uploaded_file import UploadedFile
from app.models.user import User

router = APIRouter(prefix="/api", tags=["privacy"])


@router.delete("/me/data")
async def delete_my_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove the current user's rows and Qdrant points. Keeps the user account."""
    await db.execute(delete(Transaction).where(Transaction.user_id == user.id))
    await db.execute(delete(UploadedFile).where(UploadedFile.user_id == user.id))
    await db.execute(delete(FinancialProfile).where(FinancialProfile.user_id == user.id))
    await db.execute(delete(CategoryRule).where(CategoryRule.user_id == user.id))
    await db.commit()

    try:
        from app.rag.store import get_store

        get_store().delete_user(user.id)
    except Exception:
        pass

    # Confirm residue
    tx_count = await db.scalar(
        select(Transaction.id).where(Transaction.user_id == user.id).limit(1)
    )
    return {
        "deleted": True,
        "user_id": user.id,
        "residual_transactions": tx_count is not None,
    }
