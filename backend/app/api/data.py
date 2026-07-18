import hashlib
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_db
from app.engines.profile import build_financial_profile
from app.ingestion.csv_parser import ParseResult, parse_bank_csv
from app.ingestion.pdf_parser import parse_bank_pdf
from app.models.finance import FinancialProfile, Transaction, UploadedFile
from app.models.user import User

router = APIRouter(prefix="/api", tags=["data"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/upload")
async def upload_statement(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    filename = file.filename or "statement"
    content_hash = hashlib.sha256(content).hexdigest()
    existing = (
        await db.execute(
            select(UploadedFile).where(
                UploadedFile.user_id == user.id, UploadedFile.sha256 == content_hash
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return _summary(existing, rows_added=0, duplicate=True)

    parsed = _parse_upload(filename, file.content_type or "", content)
    dates = [txn.date for txn in parsed.transactions]
    upload = UploadedFile(
        user_id=user.id,
        filename=filename,
        content_type=file.content_type or "",
        sha256=content_hash,
        rows_parsed=len(parsed.transactions),
        rows_skipped=parsed.rows_skipped,
        min_date=min(dates),
        max_date=max(dates),
    )
    db.add(upload)
    await db.flush()

    for txn in parsed.transactions:
        db.add(
            Transaction(
                user_id=user.id,
                date=txn.date,
                description=txn.description,
                amount=txn.amount,
                direction=txn.direction,
                source_file=filename,
                uploaded_file_id=upload.id,
            )
        )

    await db.commit()
    await _recompute_profile(db, user.id)
    await db.refresh(upload)
    return _summary(upload, rows_added=len(parsed.transactions), duplicate=False)


@router.get("/profile")
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    profile = (
        await db.execute(
            select(FinancialProfile).where(FinancialProfile.user_id == user.id)
        )
    ).scalar_one_or_none()
    if profile is None:
        await _recompute_profile(db, user.id)
        profile = (
            await db.execute(
                select(FinancialProfile).where(FinancialProfile.user_id == user.id)
            )
        ).scalar_one()

    transactions_count = (
        await db.execute(select(Transaction).where(Transaction.user_id == user.id))
    ).scalars().all()
    return {
        "monthly_income": _money(profile.monthly_income),
        "monthly_expenses": _money(profile.monthly_expenses),
        "surplus": _money(profile.surplus),
        "total_debt": _money(profile.total_debt),
        "emi_outgo": _money(profile.emi_outgo),
        "computed_at": profile.computed_at.isoformat() if profile.computed_at else None,
        "transactions_count": len(transactions_count),
    }


def _parse_upload(filename: str, content_type: str, content: bytes) -> ParseResult:
    lowered = filename.lower()
    try:
        if lowered.endswith(".csv") or "csv" in content_type:
            return parse_bank_csv(content)
        if lowered.endswith(".pdf") or "pdf" in content_type:
            return parse_bank_pdf(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail="Only CSV and PDF statements are supported")


async def _recompute_profile(db: AsyncSession, user_id: int) -> None:
    transactions = (
        await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.date, Transaction.id)
        )
    ).scalars().all()
    profile = build_financial_profile(user_id, list(transactions))
    await db.merge(profile)
    await db.commit()


def _summary(upload: UploadedFile, rows_added: int, duplicate: bool) -> dict:
    return {
        "file_id": upload.id,
        "filename": upload.filename,
        "rows_parsed": upload.rows_parsed,
        "rows_added": rows_added,
        "rows_skipped": upload.rows_skipped,
        "date_range": {
            "from": upload.min_date.isoformat() if upload.min_date else None,
            "to": upload.max_date.isoformat() if upload.max_date else None,
        },
        "duplicate": duplicate,
    }


def _money(value: Decimal) -> str:
    return str(Decimal(value).quantize(Decimal("0.01")))
