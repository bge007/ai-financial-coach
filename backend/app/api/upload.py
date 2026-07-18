"""Statement upload + financial profile endpoints."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.core.rate_limit import client_key, upload_limiter
from app.engines.profile import TxnInput, compute_profile
from app.ingestion.categorizer import make_default_categorizer
from app.ingestion.csv_parser import ParseError, parse_csv
from app.ingestion.pdf_parser import parse_pdf
from app.models.enums import Direction
from app.models.financial_profile import FinancialProfile
from app.models.schemas import FinancialProfileOut, ParseSummary, UploadResponse
from app.models.transaction import Transaction
from app.models.uploaded_file import UploadedFile
from app.models.user import User

router = APIRouter(prefix="/api", tags=["data"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".csv", ".pdf"}
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/pdf",
    "application/octet-stream",
    "text/plain",
}


def _extension(filename: str) -> str:
    name = (filename or "").lower()
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1]


async def _load_user_txns(db: AsyncSession, user_id: int) -> list[TxnInput]:
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    )
    rows = result.scalars().all()
    return [
        TxnInput(
            date=r.date,
            description=r.description,
            amount=Decimal(r.amount),
            direction=r.direction if isinstance(r.direction, Direction) else Direction(r.direction),
        )
        for r in rows
    ]


async def _upsert_profile(db: AsyncSession, user_id: int) -> FinancialProfile | None:
    txns = await _load_user_txns(db, user_id)
    if not txns:
        # Clear stale profile if all data gone.
        existing = await db.get(FinancialProfile, user_id)
        if existing:
            await db.delete(existing)
            await db.commit()
        return None

    result = compute_profile(txns)
    now = datetime.now(timezone.utc)
    profile = await db.get(FinancialProfile, user_id)
    if profile is None:
        profile = FinancialProfile(
            user_id=user_id,
            monthly_income=result.monthly_income,
            monthly_expenses=result.monthly_expenses,
            surplus=result.surplus,
            total_debt=result.total_debt,
            emi_outgo=result.emi_outgo,
            computed_at=now,
        )
        db.add(profile)
    else:
        profile.monthly_income = result.monthly_income
        profile.monthly_expenses = result.monthly_expenses
        profile.surplus = result.surplus
        profile.total_debt = result.total_debt
        profile.emi_outgo = result.emi_outgo
        profile.computed_at = now
    await db.commit()
    await db.refresh(profile)
    return profile


def _profile_out(profile: FinancialProfile) -> FinancialProfileOut:
    return FinancialProfileOut.model_validate(profile)


async def _index_pdf_for_rag(raw: bytes, user_id: int, filename: str) -> None:
    import io

    import pdfplumber

    from app.rag.chunking import chunk_pages
    from app.rag.store import get_store

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    chunks = chunk_pages(pages)
    if not chunks:
        return
    store = get_store()
    store.upsert_chunks(
        user_id=user_id,
        source_file=filename,
        chunks=[(c.text, c.page) for c in chunks],
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    upload_limiter.check(client_key(request, user.id))
    filename = file.filename or "upload"
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only CSV and PDF are accepted.",
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        # Be tolerant of browsers that send odd CSV MIME types when extension is ok.
        if not (ext == ".csv" and content_type.startswith("text/")):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type '{file.content_type}'.",
            )

    raw = await file.read()
    size = len(raw)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )

    digest = hashlib.sha256(raw).hexdigest()

    # Idempotency: same user + same hash → no new rows.
    existing = await db.execute(
        select(UploadedFile).where(
            UploadedFile.user_id == user.id,
            UploadedFile.sha256 == digest,
        )
    )
    prior = existing.scalar_one_or_none()
    if prior is not None:
        profile = await db.get(FinancialProfile, user.id)
        return UploadResponse(
            summary=ParseSummary(
                filename=prior.filename,
                rows_parsed=0,
                rows_skipped=0,
                date_range_start=None,
                date_range_end=None,
                duplicate=True,
                uploaded_file_id=prior.id,
            ),
            profile=_profile_out(profile) if profile else None,
        )

    try:
        if ext == ".csv":
            parsed, skipped = parse_csv(raw)
        else:
            parsed, skipped = parse_pdf(raw)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    uploaded = UploadedFile(
        user_id=user.id,
        filename=filename,
        sha256=digest,
        size=size,
    )
    db.add(uploaded)
    await db.flush()  # get uploaded.id

    categorizer = make_default_categorizer()
    categories = await categorizer.categorize_many(
        [row.description for row in parsed],
        db,
        user.id,
        use_llm=True,
    )

    for row, category in zip(parsed, categories, strict=True):
        db.add(
            Transaction(
                user_id=user.id,
                uploaded_file_id=uploaded.id,
                date=row.date,
                description=row.description,
                amount=row.amount,
                direction=row.direction,
                category=category,
                source_file=filename,
            )
        )
    await db.commit()
    await db.refresh(uploaded)

    # Index PDF text into Qdrant for RAG (CSV statements are tabular, not docs).
    if ext == ".pdf":
        try:
            await _index_pdf_for_rag(raw, user.id, filename)
        except Exception:
            # Never fail the upload if indexing is unavailable.
            pass

    profile = await _upsert_profile(db, user.id)
    dates = [t.date for t in parsed]
    return UploadResponse(
        summary=ParseSummary(
            filename=filename,
            rows_parsed=len(parsed),
            rows_skipped=skipped,
            date_range_start=min(dates) if dates else None,
            date_range_end=max(dates) if dates else None,
            duplicate=False,
            uploaded_file_id=uploaded.id,
        ),
        profile=_profile_out(profile) if profile else None,
    )


@router.get("/profile", response_model=FinancialProfileOut | None)
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinancialProfileOut | None:
    profile = await db.get(FinancialProfile, user.id)
    if profile is None:
        # Recompute from any existing transactions for this user only.
        profile = await _upsert_profile(db, user.id)
    if profile is None:
        return None
    return _profile_out(profile)
