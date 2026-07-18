"""India income tax + SIP/EPF/NPS projections from versioned YAML."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import yaml

from app.core.paths import config_dir
from app.engines.investment import project_growth

TWOPLACES = Decimal("0.01")


def _money(v: Decimal | float | int) -> Decimal:
    return Decimal(str(v)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def load_tax_config(fy: str | None = None, path: Path | None = None) -> dict[str, Any]:
    if path is not None:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg_dir = config_dir()
    if fy:
        candidate = cfg_dir / f"tax_fy{fy.replace('-', '_')}.yaml"
        if candidate.exists():
            return yaml.safe_load(candidate.read_text(encoding="utf-8"))
    # Default: newest tax_fy*.yaml
    files = sorted(cfg_dir.glob("tax_fy*.yaml"))
    if not files:
        raise FileNotFoundError("No config/tax_fy*.yaml found")
    return yaml.safe_load(files[-1].read_text(encoding="utf-8"))


def _tax_from_slabs(taxable: Decimal, slabs: list) -> Decimal:
    """Progressive slab tax on taxable income. slabs: [[upper, rate], ...] upper null = inf."""
    if taxable <= 0:
        return _money(0)
    tax = Decimal("0")
    lower = Decimal("0")
    for upper, rate in slabs:
        top = Decimal(str(upper)) if upper is not None else taxable
        if taxable <= lower:
            break
        band = min(taxable, top) - lower
        if band > 0:
            tax += band * Decimal(str(rate))
        lower = top
        if upper is None:
            break
    return _money(tax)


def compute_old_regime(
    gross_income: Decimal | float | int,
    deductions: dict[str, Decimal | float | int] | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_tax_config()
    gross = _money(gross_income)
    d = deductions or {}
    limits = cfg["old_regime"]["deductions"]
    std = _money(limits["standard_deduction"])
    d80c = min(_money(d.get("80c", 0)), _money(limits["section_80c_limit"]))
    d80d = min(_money(d.get("80d", 0)), _money(limits["section_80d_limit"]))
    d80ccd = min(
        _money(d.get("80ccd_1b", 0)),
        _money(cfg["nps"]["section_80ccd_1b_limit"]),
    )
    total_ded = std + d80c + d80d + d80ccd
    taxable = max(_money(0), gross - total_ded)
    base_tax = _tax_from_slabs(taxable, cfg["old_regime"]["slabs"])
    cess = _money(base_tax * Decimal(str(cfg["cess_rate"])))
    total = _money(base_tax + cess)
    return {
        "regime": "old",
        "financial_year": cfg["financial_year"],
        "gross_income": gross,
        "taxable_income": taxable,
        "deductions": {
            "standard_deduction": std,
            "80c": d80c,
            "80d": d80d,
            "80ccd_1b": d80ccd,
            "total": _money(total_ded),
        },
        "tax_before_cess": base_tax,
        "cess": cess,
        "total_tax": total,
    }


def compute_new_regime(
    gross_income: Decimal | float | int,
    deductions: dict[str, Decimal | float | int] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_tax_config()
    gross = _money(gross_income)
    # New regime: standard deduction only (+ optional 80CCD(1B) if provided).
    std = _money(cfg["new_regime"]["standard_deduction"])
    d = deductions or {}
    d80ccd = min(
        _money(d.get("80ccd_1b", 0)),
        _money(cfg["nps"]["section_80ccd_1b_limit"]),
    )
    total_ded = std + d80ccd
    taxable = max(_money(0), gross - total_ded)
    base_tax = _tax_from_slabs(taxable, cfg["new_regime"]["slabs"])
    cess = _money(base_tax * Decimal(str(cfg["cess_rate"])))
    total = _money(base_tax + cess)
    return {
        "regime": "new",
        "financial_year": cfg["financial_year"],
        "gross_income": gross,
        "taxable_income": taxable,
        "deductions": {
            "standard_deduction": std,
            "80ccd_1b": d80ccd,
            "total": _money(total_ded),
        },
        "tax_before_cess": base_tax,
        "cess": cess,
        "total_tax": total,
    }


def compare_regimes(
    gross_income: Decimal | float | int,
    deductions: dict[str, Decimal | float | int] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_tax_config()
    old = compute_old_regime(gross_income, deductions, cfg)
    new = compute_new_regime(gross_income, deductions, cfg)
    better = "old" if old["total_tax"] < new["total_tax"] else "new"
    if old["total_tax"] == new["total_tax"]:
        better = "either"
    return {
        "financial_year": cfg["financial_year"],
        "old": old,
        "new": new,
        "better_regime": better,
        "savings_vs_other": _money(abs(old["total_tax"] - new["total_tax"])),
    }


def sip_maturity(
    monthly: Decimal | float | int,
    years: int,
    annual_return: Decimal | float = Decimal("0.12"),
) -> Decimal:
    return project_growth(monthly, years, annual_return)


def epf_projection(
    monthly: Decimal | float | int,
    years: int,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project EPF corpus: employee+employer contribution earn interest_rate."""
    cfg = config or load_tax_config()
    rate = Decimal(str(cfg["epf"]["interest_rate"]))
    emp = Decimal(str(cfg["epf"]["employee_rate"]))
    er = Decimal(str(cfg["epf"]["employer_rate"]))
    # monthly here is basic salary contribution base
    base = _money(monthly)
    contrib = _money(base * (emp + er))
    corpus = project_growth(contrib, years, rate)
    return {
        "monthly_contribution": contrib,
        "years": years,
        "interest_rate": rate,
        "corpus": corpus,
        "financial_year": cfg["financial_year"],
    }


def nps_projection(
    monthly: Decimal | float | int,
    years: int,
    annual_return: Decimal | float = Decimal("0.10"),
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or load_tax_config()
    corpus = project_growth(monthly, years, annual_return)
    return {
        "monthly_contribution": _money(monthly),
        "years": years,
        "expected_return": Decimal(str(annual_return)),
        "corpus": corpus,
        "80ccd_1b_limit": _money(cfg["nps"]["section_80ccd_1b_limit"]),
        "financial_year": cfg["financial_year"],
    }
