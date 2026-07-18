from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from statistics import median

from app.models.finance import FinancialProfile, Transaction


SELF_TRANSFER_KEYWORDS = (
    "self transfer",
    "own account",
    "internal transfer",
    "upi self",
    "to self",
    "from self",
)
EMI_KEYWORDS = ("emi", "loan")


@dataclass(frozen=True)
class ProfileNumbers:
    monthly_income: Decimal
    monthly_expenses: Decimal
    surplus: Decimal
    total_debt: Decimal
    emi_outgo: Decimal


def derive_profile_numbers(transactions: list[Transaction]) -> ProfileNumbers:
    monthly_credits: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    monthly_debits: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    emi_candidates: dict[tuple[str, Decimal], set[str]] = defaultdict(set)

    for txn in transactions:
        month = txn.date.strftime("%Y-%m")
        amount = Decimal(txn.amount).quantize(Decimal("0.01"))
        description = txn.description.lower()
        if txn.direction == "credit":
            if not any(keyword in description for keyword in SELF_TRANSFER_KEYWORDS):
                monthly_credits[month] += amount
        elif txn.direction == "debit":
            monthly_debits[month] += amount
            if any(keyword in description for keyword in EMI_KEYWORDS):
                normalized_desc = _normalize_recurring_description(description)
                emi_candidates[(normalized_desc, amount)].add(month)

    monthly_income = _median_amount(monthly_credits.values())
    monthly_expenses = _median_amount(monthly_debits.values())
    emi_outgo = sum(
        (
            amount
            for (_description, amount), months in emi_candidates.items()
            if len(months) >= 2
        ),
        Decimal("0.00"),
    )
    emi_outgo = emi_outgo.quantize(Decimal("0.01"))
    surplus = (monthly_income - monthly_expenses).quantize(Decimal("0.01"))

    return ProfileNumbers(
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        surplus=surplus,
        total_debt=Decimal("0.00"),
        emi_outgo=emi_outgo,
    )


def build_financial_profile(user_id: int, transactions: list[Transaction]) -> FinancialProfile:
    numbers = derive_profile_numbers(transactions)
    return FinancialProfile(
        user_id=user_id,
        monthly_income=numbers.monthly_income,
        monthly_expenses=numbers.monthly_expenses,
        surplus=numbers.surplus,
        total_debt=numbers.total_debt,
        emi_outgo=numbers.emi_outgo,
        computed_at=datetime.now(timezone.utc),
    )


def _median_amount(values) -> Decimal:
    amounts = [Decimal(value).quantize(Decimal("0.01")) for value in values]
    if not amounts:
        return Decimal("0.00")
    return Decimal(str(median(amounts))).quantize(Decimal("0.01"))


def _normalize_recurring_description(description: str) -> str:
    return " ".join(part for part in description.split() if not part.isdigit())
