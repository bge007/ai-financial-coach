from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import Category, Direction


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    uploaded_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("uploaded_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(1024))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    direction: Mapped[Direction] = mapped_column(
        Enum(Direction, name="direction_enum", native_enum=False)
    )
    category: Mapped[Category | None] = mapped_column(
        Enum(Category, name="category_enum", native_enum=False),
        nullable=True,
    )
    source_file: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    uploaded_file = relationship("UploadedFile", back_populates="transactions")
