from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    monthly_income: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    monthly_expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    surplus: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    total_debt: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    emi_outgo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
