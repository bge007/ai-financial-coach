from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    direction: Mapped[str] = mapped_column(String(16))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_file: Mapped[str] = mapped_column(String(255))
    uploaded_file_id: Mapped[int] = mapped_column(ForeignKey("uploaded_files.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    __table_args__ = (
        UniqueConstraint("user_id", "sha256", name="uq_uploaded_files_user_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    rows_parsed: Mapped[int] = mapped_column(default=0)
    rows_skipped: Mapped[int] = mapped_column(default=0)
    min_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FinancialProfile(Base):
    __tablename__ = "financial_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    monthly_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    monthly_expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    surplus: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total_debt: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    emi_outgo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
