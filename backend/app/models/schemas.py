from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.enums import Category, Direction


class ParsedTransaction(BaseModel):
    """Normalized row produced by CSV/PDF parsers before persistence."""

    date: date
    description: str
    amount: Decimal = Field(gt=0)
    direction: Direction


class ParseSummary(BaseModel):
    filename: str
    rows_parsed: int
    rows_skipped: int
    date_range_start: date | None = None
    date_range_end: date | None = None
    duplicate: bool = False
    uploaded_file_id: int | None = None


class UploadResponse(BaseModel):
    summary: ParseSummary
    profile: "FinancialProfileOut | None" = None


class FinancialProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    monthly_income: Decimal
    monthly_expenses: Decimal
    surplus: Decimal
    total_debt: Decimal
    emi_outgo: Decimal
    computed_at: datetime
    # Bank statements rarely expose outstanding principal; Phase 1 leaves this at 0.
    total_debt_note: str = (
        "total_debt is 0 when statements provide no outstanding principal"
    )


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    description: str
    amount: Decimal
    direction: Direction
    category: Category | None
    source_file: str


class TransactionListOut(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int
    available_months: list[str] = []


class RecategorizeIn(BaseModel):
    category: Category


class RecategorizeOut(BaseModel):
    transaction: TransactionOut
    rule_id: int


class UserProfileIn(BaseModel):
    name: str = ""
    age: int | None = Field(default=None, ge=18, le=100)
    city: str = ""
    monthly_income: Decimal | None = Field(default=None, ge=0)
    emergency_fund: Decimal | None = Field(default=None, ge=0)
    risk_profile: str = Field(default="moderate")


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    age: int | None
    city: str
    monthly_income: Decimal | None
    emergency_fund: Decimal | None
    risk_profile: str
    updated_at: datetime


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    dob: date
    gender: Literal["female", "male", "other", "prefer_not_to_say"]
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Name is required")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()

    @model_validator(mode="after")
    def passwords_match(self) -> "SignupIn":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()


class AuthUserOut(BaseModel):
    id: int
    email: str
    name: str
    dob: date | None = None
    gender: str | None = None
