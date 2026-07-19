"""My Money Mitra — premium services API."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import tools
from app.core.auth import get_current_user
from app.core.db import get_db
from app.core.rate_limit import ask_limiter, client_key
from app.engines.consultation import (
    TOPIC_LABELS,
    VALID_TIME_SLOTS,
    VALID_TOPICS,
    expert_chat_reply,
)
from app.engines.premium import (
    analyze_cibil_tips,
    detect_subscriptions,
    subscription_summary,
)
from app.engines.profile import TxnInput
from app.models.consultation_booking import ConsultationBooking
from app.models.transaction import Transaction
from app.models.user import User

router = APIRouter(prefix="/api/premium", tags=["premium"])


def _txn_rows(rows: list[Transaction]) -> list[TxnInput]:
    return [
        TxnInput(
            date=t.date,
            description=t.description,
            amount=t.amount,
            direction=t.direction,
        )
        for t in rows
    ]


def _booking_out(row: ConsultationBooking) -> dict[str, Any]:
    return {
        "id": row.id,
        "topic": row.topic,
        "topic_label": TOPIC_LABELS.get(row.topic, row.topic),
        "preferred_date": row.preferred_date.isoformat(),
        "preferred_time": row.preferred_time,
        "contact_phone": row.contact_phone,
        "notes": row.notes,
        "status": row.status,
        "expert_rating": row.expert_rating,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
    }


async def _latest_booking(db: AsyncSession, user_id: int) -> ConsultationBooking | None:
    result = await db.execute(
        select(ConsultationBooking)
        .where(
            ConsultationBooking.user_id == user_id,
            ConsultationBooking.status == "scheduled",
        )
        .order_by(ConsultationBooking.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


class ConsultationBookIn(BaseModel):
    topic: str = Field(min_length=1, max_length=64)
    preferred_date: date
    preferred_time: str = Field(min_length=1, max_length=32)
    contact_phone: str = Field(default="", max_length=32)
    notes: str = Field(default="", max_length=1024)


class ConsultationChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    booking_id: int | None = None


class ConsultationCloseIn(BaseModel):
    booking_id: int
    rating: int | None = Field(default=None, ge=1, le=5)


@router.get("")
async def premium_services(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    profile = await tools.get_profile(db, user.id)
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.date.desc())
    )
    rows = list(result.scalars().all())
    txn_inputs = _txn_rows(rows)
    subs = detect_subscriptions(txn_inputs)
    cibil = analyze_cibil_tips(profile, txn_inputs, subs)
    booking = await _latest_booking(db, user.id)

    return {
        "report": {
            "available": bool(profile or rows),
            "download_path": "/api/report/consolidated.pdf",
            "description": (
                "Consolidated PDF covering Dashboard, Data & Profile, Transactions, "
                "Analytics, Budget, Investment, Portfolio, Tax and Coach modules."
            ),
        },
        "cibil": cibil,
        "subscriptions": subscription_summary(subs),
        "has_data": bool(rows),
        "consultation": {
            "topics": [{"id": k, "label": v} for k, v in TOPIC_LABELS.items()],
            "time_slots": [
                {"id": "morning", "label": "Morning (9 AM – 12 PM)"},
                {"id": "afternoon", "label": "Afternoon (12 PM – 4 PM)"},
                {"id": "evening", "label": "Evening (4 PM – 8 PM)"},
            ],
            "booking": _booking_out(booking) if booking else None,
        },
    }


@router.post("/consultation/book")
async def book_consultation(
    body: ConsultationBookIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if body.topic not in VALID_TOPICS:
        raise HTTPException(status_code=400, detail=f"Unknown topic '{body.topic}'")
    if body.preferred_time not in VALID_TIME_SLOTS:
        raise HTTPException(status_code=400, detail=f"Unknown time slot '{body.preferred_time}'")
    if body.preferred_date < date.today():
        raise HTTPException(status_code=400, detail="Preferred date must be today or later.")

    row = ConsultationBooking(
        user_id=user.id,
        topic=body.topic,
        preferred_date=body.preferred_date,
        preferred_time=body.preferred_time,
        contact_phone=body.contact_phone.strip(),
        notes=body.notes.strip(),
        status="scheduled",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"booking": _booking_out(row)}


@router.post("/consultation/close")
async def close_consultation(
    body: ConsultationCloseIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    booking = await db.get(ConsultationBooking, body.booking_id)
    if not booking or booking.user_id != user.id:
        raise HTTPException(status_code=404, detail="Consultation booking not found.")
    if booking.status != "scheduled":
        raise HTTPException(status_code=400, detail="Consultation is already closed.")

    booking.status = "completed"
    booking.expert_rating = body.rating
    booking.closed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(booking)
    return {"booking": _booking_out(booking)}


@router.post("/consultation/chat")
async def consultation_chat(
    request: Request,
    body: ConsultationChatIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ask_limiter.check(client_key(request, user.id))

    if body.booking_id:
        booking = await db.get(ConsultationBooking, body.booking_id)
        if not booking or booking.user_id != user.id:
            raise HTTPException(status_code=404, detail="Consultation booking not found.")
    else:
        booking = await _latest_booking(db, user.id)
    if not booking:
        raise HTTPException(
            status_code=400,
            detail="Book a consultation before using the expert chat.",
        )

    reply, warning = await expert_chat_reply(db, user.id, booking, body.message)

    async def event_stream():
        meta: dict[str, Any] = {
            "booking_id": booking.id,
            "topic_label": TOPIC_LABELS.get(booking.topic, booking.topic),
        }
        if warning:
            meta["llm_warning"] = warning
        yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
        step = 80
        for i in range(0, len(reply), step):
            yield f"event: token\ndata: {json.dumps({'text': reply[i:i+step]})}\n\n"
        yield f"event: done\ndata: {json.dumps({'reply': reply})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
