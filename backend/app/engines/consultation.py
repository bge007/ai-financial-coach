"""Consultation expert chat — context from user profile (no invented numbers)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import tools
from app.agents.llm import DISCLAIMER, consultation_expert_reply
from app.models.consultation_booking import ConsultationBooking

TOPIC_LABELS = {
    "financial_planning": "Financial planning",
    "budgeting": "Budgeting & cash flow",
    "investments": "Investments & SIPs",
    "tax_retirement": "Tax & retirement",
    "debt_emi": "Debt & EMI management",
    "general": "General money guidance",
}

VALID_TOPICS = set(TOPIC_LABELS)
VALID_TIME_SLOTS = {"morning", "afternoon", "evening"}

EXPERT_SYSTEM = f"""You are Money Mitra, the user's personal finance guide in a live 1-on-1 consultation chat.
Introduce yourself warmly when appropriate. The client booked a session for budgeting, financial planning, or related money topics in India.

Rules:
- Answer clearly in 2-4 short paragraphs with bullet steps when helpful.
- NEVER invent rupee amounts, rates, or tax figures — only use numbers from Client context.
- If data is missing, tell them what to upload on Data & Profile or which advisor module to open.
- Stay practical: budgets, surplus, EMIs, subscriptions, savings habits, next actions.
- Do not recommend specific stocks or guaranteed returns.

{DISCLAIMER}"""


async def build_client_context(db: AsyncSession, user_id: int) -> str:
    profile = await tools.get_profile(db, user_id)
    lines = ["Client context:"]
    if profile:
        lines.extend(
            [
                f"- Monthly income (computed): Rs. {profile['monthly_income']}",
                f"- Monthly expenses (computed): Rs. {profile['monthly_expenses']}",
                f"- Surplus: Rs. {profile['surplus']}",
                f"- EMI outgo: Rs. {profile.get('emi_outgo') or 0}",
                f"- Total debt (est.): Rs. {profile.get('total_debt') or 0}",
            ]
        )
    else:
        lines.append("- No computed profile yet — suggest uploading a bank statement.")
    return "\n".join(lines)


def format_booking_context(booking: ConsultationBooking) -> str:
    topic = TOPIC_LABELS.get(booking.topic, booking.topic)
    return (
        f"Booked consultation topic: {topic}\n"
        f"Preferred slot: {booking.preferred_date} ({booking.preferred_time})\n"
        f"Client notes: {booking.notes or 'None'}"
    )


async def expert_chat_reply(
    db: AsyncSession,
    user_id: int,
    booking: ConsultationBooking,
    message: str,
) -> tuple[str, str | None]:
    """Return (reply_text, llm_warning)."""
    context = await build_client_context(db, user_id)
    booking_ctx = format_booking_context(booking)
    user_prompt = f"{context}\n\n{booking_ctx}\n\nClient question:\n{message.strip()}"
    reply, warning = await consultation_expert_reply(EXPERT_SYSTEM, user_prompt)
    return reply, warning
