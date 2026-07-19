"""Tests for premium subscription detection and CIBIL tips."""

from datetime import date
from decimal import Decimal

from app.engines.premium import (
    analyze_cibil_tips,
    detect_subscriptions,
    subscription_summary,
)
from app.engines.profile import TxnInput
from app.models.enums import Direction


def _debit(d: str, desc: str, amt: str) -> TxnInput:
    y, m, day = map(int, d.split("-"))
    return TxnInput(
        date=date(y, m, day),
        description=desc,
        amount=Decimal(amt),
        direction=Direction.debit,
    )


def test_detect_subscriptions_netflix_hotstar():
    txns = [
        _debit("2026-01-05", "UPI/NETFLIX COM", "199"),
        _debit("2026-02-05", "UPI/NETFLIX COM", "199"),
        _debit("2026-01-12", "HOTSTAR SUBSCRIPTION", "299"),
        _debit("2026-02-12", "HOTSTAR SUBSCRIPTION", "299"),
    ]
    hits = detect_subscriptions(txns)
    names = {h.name for h in hits}
    assert "Netflix" in names
    assert "Disney+ Hotstar" in names
    netflix = next(h for h in hits if h.name == "Netflix")
    assert netflix.amount == Decimal("199.00")
    assert netflix.frequency == "monthly"


def test_subscription_summary_monthly_total():
    txns = [
        _debit("2026-01-05", "NETFLIX", "199"),
        _debit("2026-02-05", "NETFLIX", "199"),
        _debit("2026-01-10", "JIO PREPAID", "666"),
        _debit("2026-02-10", "JIO PREPAID", "666"),
    ]
    hits = detect_subscriptions(txns)
    summary = subscription_summary(hits)
    assert summary["count"] >= 2
    assert Decimal(summary["monthly_total"]) >= Decimal("865.00")


def test_cibil_tips_flags_bounce_and_high_emi():
    txns = [
        _debit("2026-01-05", "CHEQUE BOUNCE CHARGES", "500"),
        _debit("2026-01-07", "HOME LOAN EMI", "45000"),
        _debit("2026-02-07", "HOME LOAN EMI", "45000"),
    ]
    profile = {
        "monthly_income": Decimal("80000"),
        "monthly_expenses": Decimal("75000"),
        "surplus": Decimal("5000"),
        "emi_outgo": Decimal("45000"),
    }
    result = analyze_cibil_tips(profile, txns, [])
    titles = [t["title"] for t in result["tips"]]
    assert any("bounce" in t.lower() for t in titles)
    assert any("EMI" in t for t in titles)
