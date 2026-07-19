"""Consolidated PDF report export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.reports.consolidated import build_consolidated_sections
from app.reports.pdf_builder import build_consolidated_pdf

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/consolidated.pdf")
async def export_consolidated_pdf(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    user_profile = await db.get(UserProfile, user.id)
    try:
        report = await build_consolidated_sections(db, user, user_profile)
        pdf_bytes = build_consolidated_pdf(report)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not generate report: {exc}",
        ) from exc

    filename = f"MoneyMitra-Report-{user.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
