"""Risk allocation and SIP growth projection — YAML-driven, no LLM."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import yaml

from app.core.paths import config_path

TWOPLACES = Decimal("0.01")
_CONFIG = config_path("risk_allocation.yaml")


def _money(v: Decimal | float | int) -> Decimal:
    return Decimal(str(v)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def load_risk_config(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))


def risk_allocation(
    age: int,
    risk_profile: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Decimal]:
    """Return {equity, debt, cash} shares that sum to 1.00."""
    cfg = config or load_risk_config()
    profile = (risk_profile or "moderate").lower().strip()
    base = dict(cfg["profiles"].get(profile) or cfg["profiles"]["moderate"])
    equity = float(base["equity"])
    debt = float(base["debt"])
    cash = float(base["cash"])

    # Mild age tilt for non-conservative profiles: reduce equity as age rises.
    if profile != "conservative" and age > 0:
        factor = max(0.4, (100 - age) / 100)
        new_equity = equity * factor
        freed = equity - new_equity
        equity = new_equity
        debt += freed * 0.8
        cash += freed * 0.2

    total = equity + debt + cash
    return {
        "equity": _money(Decimal(str(equity / total))),
        "debt": _money(Decimal(str(debt / total))),
        "cash": _money(Decimal(str(cash / total))),
    }


def project_growth(
    monthly_amount: Decimal | float | int,
    years: int,
    expected_return: Decimal | float,
) -> Decimal:
    """SIP future value with monthly compounding.

    FV = P * [((1+i)^n − 1) / i] * (1+i)
    where i = annual_return/12, n = years*12, P = monthly_amount.
    """
    p = Decimal(str(monthly_amount))
    if p <= 0 or years <= 0:
        return _money(0)
    annual = Decimal(str(expected_return))
    i = annual / Decimal(12)
    n = years * 12
    if i == 0:
        return _money(p * n)
    # Use float pow for intermediate, then quantize.
    growth = (Decimal("1") + i) ** n
    fv = p * ((growth - Decimal("1")) / i) * (Decimal("1") + i)
    return _money(fv)


def blended_expected_return(
    allocation: dict[str, Decimal],
    config: dict[str, Any] | None = None,
) -> Decimal:
    cfg = config or load_risk_config()
    rets = cfg.get("expected_returns") or {}
    total = Decimal("0")
    for asset, weight in allocation.items():
        r = Decimal(str(rets.get(asset, 0)))
        total += Decimal(str(weight)) * r
    return total.quantize(Decimal("0.0001"))
