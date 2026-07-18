from datetime import date
from decimal import Decimal

from app.engines.profile import TxnInput, compute_profile, is_self_transfer
from app.models.enums import Direction


def _t(d: str, desc: str, amount: str, direction: Direction) -> TxnInput:
    return TxnInput(
        date=date.fromisoformat(d),
        description=desc,
        amount=Decimal(amount),
        direction=direction,
    )


def test_self_transfer_detection():
    assert is_self_transfer("SELF TRANSFER FROM OWN AC")
    assert is_self_transfer("UPI/self/123")
    assert not is_self_transfer("SALARY CREDIT NEFT")


def test_profile_matches_hand_computed_fixture_math():
    """Hand-worked arithmetic on the HDFC/ICICI/SBI fixture shape.

    Monthly eligible credits (self-transfer ₹5,000 excluded):
      Jan 100000, Feb 100000, Mar 110000
      median = 100000

    Monthly debits:
      Jan 25000+8000+15000+3000 = 51000
      Feb 25000+9000+15000+5000 = 54000
      Mar 25000+7000+15000+4000 = 51000
      median = 51000

    surplus = 100000 - 51000 = 49000
    emi_outgo = 15000 (same EMI amount in ≥2 months)
    total_debt = 0 (no outstanding principal in statements)
    """
    txns = [
        _t("2026-01-01", "SALARY CREDIT NEFT ACME CORP", "100000", Direction.credit),
        _t("2026-01-02", "SELF TRANSFER FROM OWN AC", "5000", Direction.credit),
        _t("2026-01-05", "RENT PAYMENT UPI", "25000", Direction.debit),
        _t("2026-01-10", "GROCERIES BIGBAZAAR", "8000", Direction.debit),
        _t("2026-01-15", "EMI HDFC LOAN", "15000", Direction.debit),
        _t("2026-01-20", "DINING SWIGGY", "3000", Direction.debit),
        _t("2026-02-01", "SALARY CREDIT NEFT ACME CORP", "100000", Direction.credit),
        _t("2026-02-05", "RENT PAYMENT UPI", "25000", Direction.debit),
        _t("2026-02-10", "GROCERIES BIGBAZAAR", "9000", Direction.debit),
        _t("2026-02-15", "EMI HDFC LOAN", "15000", Direction.debit),
        _t("2026-02-22", "SHOPPING AMAZON", "5000", Direction.debit),
        _t("2026-03-01", "SALARY CREDIT NEFT ACME CORP", "110000", Direction.credit),
        _t("2026-03-05", "RENT PAYMENT UPI", "25000", Direction.debit),
        _t("2026-03-10", "GROCERIES BIGBAZAAR", "7000", Direction.debit),
        _t("2026-03-15", "EMI HDFC LOAN", "15000", Direction.debit),
        _t("2026-03-18", "UTILITIES BESCOM", "4000", Direction.debit),
    ]

    profile = compute_profile(txns)
    assert profile.monthly_income == Decimal("100000.00")
    assert profile.monthly_expenses == Decimal("51000.00")
    assert profile.surplus == Decimal("49000.00")
    assert profile.emi_outgo == Decimal("15000.00")
    assert profile.total_debt == Decimal("0.00")


def test_empty_transactions_yield_zeros():
    profile = compute_profile([])
    assert profile.monthly_income == Decimal("0.00")
    assert profile.monthly_expenses == Decimal("0.00")
    assert profile.surplus == Decimal("0.00")
    assert profile.emi_outgo == Decimal("0.00")
