"""Deterministic financial-profile derivation from transactions.

No LLM calls. No I/O. Pure functions over already-normalized rows.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Iterable, Sequence

from app.models.enums import Direction

TWOPLACES = Decimal("0.01")

# Conservative self-transfer narration markers (India NEFT/IMPS/UPI patterns).
_SELF_TRANSFER_RE = re.compile(
    r"("
    r"self\s*transfer|transfer\s*to\s*self|own\s*account|"
    r"to\s*own\s*a/?c|self\s*a/?c|self\s*acct|"
    r"funds?\s*transfer\s*self|upi.*self|"
    r"trf\s*to\s*self"
    r")",
    re.IGNORECASE,
)

_EMI_RE = re.compile(
    r"\b(emi|loan\s*emi|loan\s*instal+ment|loan\s*repayment|ecs\s*loan)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TxnInput:
    date: date
    description: str
    amount: Decimal
    direction: Direction


@dataclass(frozen=True)
class ProfileResult:
    monthly_income: Decimal
    monthly_expenses: Decimal
    surplus: Decimal
    total_debt: Decimal
    emi_outgo: Decimal


def is_self_transfer(description: str) -> bool:
    return bool(_SELF_TRANSFER_RE.search(description or ""))


def is_emi_narration(description: str) -> bool:
    return bool(_EMI_RE.search(description or ""))


def _month_key(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def _money(value: Decimal | float | int) -> Decimal:
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _median_monthly(totals: dict[tuple[int, int], Decimal]) -> Decimal:
    if not totals:
        return Decimal("0.00")
    return _money(median([float(v) for v in totals.values()]))


def detect_emi_outgo(transactions: Sequence[TxnInput]) -> Decimal:
    """Sum of recurring same-amount EMI/LOAN debits (monthly outgo).

    A candidate is a debit whose narration matches EMI/LOAN keywords and whose
    exact amount appears in at least two distinct calendar months.
    """
    # amount → set of months it appeared
    by_amount: dict[Decimal, set[tuple[int, int]]] = defaultdict(set)
    for txn in transactions:
        if txn.direction != Direction.debit:
            continue
        if not is_emi_narration(txn.description):
            continue
        by_amount[_money(txn.amount)].add(_month_key(txn.date))

    emi_total = Decimal("0.00")
    for amount, months in by_amount.items():
        if len(months) >= 2:
            emi_total += amount
    return _money(emi_total)


def compute_profile(transactions: Iterable[TxnInput]) -> ProfileResult:
    """Derive FinancialProfile fields from a user's transactions.

    - monthly_income  = median of monthly *eligible* credit totals
      (self-transfers excluded)
    - monthly_expenses = median of monthly debit totals
    - surplus = income − expenses
    - emi_outgo = sum of recurring EMI/LOAN debit amounts
    - total_debt = 0  (statements do not expose outstanding principal)
    """
    txns = list(transactions)
    credit_by_month: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    debit_by_month: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))

    for txn in txns:
        key = _month_key(txn.date)
        amt = _money(txn.amount)
        if txn.direction == Direction.credit:
            if is_self_transfer(txn.description):
                continue
            credit_by_month[key] += amt
        else:
            debit_by_month[key] += amt

    income = _median_monthly(credit_by_month)
    expenses = _median_monthly(debit_by_month)
    surplus = _money(income - expenses)
    emi_outgo = detect_emi_outgo(txns)

    return ProfileResult(
        monthly_income=income,
        monthly_expenses=expenses,
        surplus=surplus,
        total_debt=Decimal("0.00"),
        emi_outgo=emi_outgo,
    )
