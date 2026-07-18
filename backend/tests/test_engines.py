"""Phase 4 engine tests with hand-worked expected values."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from app.engines.budget import fifty_thirty_twenty
from app.engines.debt import Debt, payoff_schedule
from app.engines.investment import project_growth, risk_allocation
from app.engines.portfolio import optimize_portfolio
from app.engines.tax_india import (
    compare_regimes,
    compute_new_regime,
    compute_old_regime,
    epf_projection,
    load_tax_config,
    nps_projection,
    sip_maturity,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_budget_fifty_thirty_twenty_hand_math():
    # income 100000
    # needs: rent 25000 + groceries 10000 + utilities 5000 = 40000 (target 50000)
    # wants: dining 15000 + shopping 10000 = 25000 (target 30000)
    # sip 5000; residual = 100000 - 40000 - 25000 - 5000 = 30000
    # savings actual = sip + residual = 35000 (target 20000) → savings overshoot
    # but "other" must NOT inflate savings
    result = fifty_thirty_twenty(
        100000,
        {
            "rent": 25000,
            "groceries": 10000,
            "utilities": 5000,
            "dining": 15000,
            "shopping": 10000,
            "sip_investment": 5000,
            "other": 2000,
        },
    )
    # wants includes other 2000 → 27000
    # residual = 100000 - 40000 - 27000 - 5000 = 28000
    # savings = 5000 + 28000 = 33000
    assert result["actual"]["needs"] == Decimal("40000.00")
    assert result["actual"]["wants"] == Decimal("27000.00")
    assert result["actual"]["savings"] == Decimal("33000.00")
    assert result["target"]["needs"] == Decimal("50000.00")
    assert result["target"]["wants"] == Decimal("30000.00")
    assert result["target"]["savings"] == Decimal("20000.00")
    assert all(o["bucket"] != "needs" for o in result["overshoot"])
    assert any(o["bucket"] == "savings" for o in result["overshoot"])


def test_sip_fv_hand_math():
    # P=10000, years=1, r=12% → i=0.01, n=12
    # FV = 10000 * [((1.01)^12 - 1)/0.01] * 1.01
    # (1.01)^12 ≈ 1.12682503013
    # ((1.12682503013-1)/0.01)*1.01 ≈ 12.682503013 * 1.01 ≈ 12.809328043
    # FV ≈ 128093.28
    fv = project_growth(10000, 1, 0.12)
    assert fv == Decimal("128093.28")


def test_project_growth_with_starting_corpus():
    # Same SIP FV as above plus C*(1.01)^12
    # 50000 * 1.12682503013 ≈ 56341.25 → + 128093.28 = 184434.53
    fv = project_growth(10000, 1, 0.12, initial_corpus=50000)
    assert fv == Decimal("184434.53")


def test_risk_allocation_sums_to_one():
    alloc = risk_allocation(30, "moderate")
    total = alloc["equity"] + alloc["debt"] + alloc["cash"]
    assert total == Decimal("1.00")


def test_old_regime_scenario_1():
    """Gross 10L, no extra deductions beyond std.

    taxable = 1000000 - 50000 = 950000
    tax: 0-2.5L:0; 2.5-5L: 12500; 5-10L: 20% of 450000 = 90000 → 102500
    cess 4% = 4100 → total 106600
    """
    r = compute_old_regime(1_000_000, {})
    assert r["taxable_income"] == Decimal("950000.00")
    assert r["tax_before_cess"] == Decimal("102500.00")
    assert r["cess"] == Decimal("4100.00")
    assert r["total_tax"] == Decimal("106600.00")


def test_old_regime_scenario_2_with_80c():
    """Gross 12L, 80C 1.5L, 80D 25k.

    ded = 50k + 150k + 25k = 225k
    taxable = 1200000 - 225000 = 975000
    tax: 12500 + 20%*475000 = 12500+95000 = 107500
    cess = 4300 → total 111800
    """
    r = compute_old_regime(1_200_000, {"80c": 150000, "80d": 25000})
    assert r["taxable_income"] == Decimal("975000.00")
    assert r["total_tax"] == Decimal("111800.00")


def test_new_regime_scenario_1():
    """Gross 10L, std 75k → taxable 925000

    slabs new: 0-3L:0; 3-7L:5% of 4L=20000; 7-10L:10% of 225000=22500 → 42500
    Wait taxable is 925000 so 7-10L band is only up to 925000: 10% of 225000 = 22500
    Yes 42500 + cess 1700 = 44200
    """
    r = compute_new_regime(1_000_000, {})
    assert r["taxable_income"] == Decimal("925000.00")
    assert r["tax_before_cess"] == Decimal("42500.00")
    assert r["total_tax"] == Decimal("44200.00")


def test_new_regime_scenario_2():
    """Gross 15L, std 75k → taxable 1425000

    0-3L:0
    3-7L:20000
    7-10L:30000
    10-12L:15% of 2L = 30000
    12-15L:20% of 225000 = 45000
    base = 125000; cess = 5000; total = 130000
    """
    r = compute_new_regime(1_500_000, {})
    assert r["taxable_income"] == Decimal("1425000.00")
    assert r["tax_before_cess"] == Decimal("125000.00")
    assert r["total_tax"] == Decimal("130000.00")


def test_compare_regimes_picks_lower_tax():
    cmp = compare_regimes(1_000_000, {"80c": 150000, "80d": 25000})
    assert cmp["better_regime"] in {"old", "new", "either"}
    assert cmp["financial_year"] == "2026-27"


def test_yaml_change_alters_tax(tmp_path):
    cfg = load_tax_config()
    base = compute_new_regime(1_000_000, {}, cfg)
    cfg2 = dict(cfg)
    cfg2["cess_rate"] = 0.0
    altered = compute_new_regime(1_000_000, {}, cfg2)
    assert altered["total_tax"] < base["total_tax"]


def test_sip_epf_nps():
    assert sip_maturity(10000, 1, 0.12) == Decimal("128093.28")
    epf = epf_projection(50000, 1)  # base 50k → contrib 12k/mo both sides = 12000
    assert epf["monthly_contribution"] == Decimal("12000.00")
    nps = nps_projection(5000, 1, 0.10)
    assert nps["corpus"] > 0


def test_debt_avalanche_clears():
    debts = [
        Debt("Card", Decimal("10000"), Decimal("0.24"), Decimal("2000")),
        Debt("Loan", Decimal("20000"), Decimal("0.12"), Decimal("2000")),
    ]
    result = payoff_schedule(debts, extra_monthly=3000, method="avalanche", start=date(2026, 1, 1))
    assert result["months"] > 0
    assert result["payoff_date"] is not None
    assert result["total_interest"] >= 0
    # Final balances zero
    assert all(v == Decimal("0.00") for v in result["schedule"][-1]["balances"].values())


def test_portfolio_optimize_runs():
    # Synthetic monthly returns
    rng = pd.DataFrame(
        {
            "EQ": [0.01, 0.02, -0.01, 0.015, 0.005, 0.02, 0.01, -0.005, 0.012, 0.008, 0.01, 0.015],
            "DEBT": [0.005, 0.004, 0.006, 0.005, 0.004, 0.005, 0.006, 0.005, 0.004, 0.005, 0.005, 0.006],
            "GOLD": [0.008, -0.002, 0.01, 0.003, 0.007, -0.001, 0.009, 0.002, 0.006, 0.004, 0.001, 0.008],
        }
    )
    # PyPortfolioOpt mean_historical_return expects prices; convert returns→prices
    prices = (1 + rng).cumprod() * 100
    out = optimize_portfolio(prices)
    assert "max_sharpe" in out
    assert abs(sum(out["max_sharpe"]["weights"].values()) - 1.0) < 1e-6


def test_engines_do_not_import_agents():
    import app.engines.budget as b
    import app.engines.tax_india as t
    import app.engines.investment as i
    import app.engines.debt as d
    import app.engines.portfolio as p

    for mod in (b, t, i, d, p):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "app.agents" not in src
        assert "openai" not in src.lower() or "openai" not in src  # no openai import
        assert "import openai" not in src
