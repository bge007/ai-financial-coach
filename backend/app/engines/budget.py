"""50/30/20 budget analysis — pure functions, YAML bucket map."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import yaml

from app.core.paths import config_path

TWOPLACES = Decimal("0.01")
_CONFIG = config_path("budget_buckets.yaml")


def _money(v: Decimal | float | int) -> Decimal:
    return Decimal(str(v)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def load_budget_config(path=None) -> dict[str, Any]:
    return yaml.safe_load((path or _CONFIG).read_text(encoding="utf-8"))


def fifty_thirty_twenty(
    income: Decimal | float | int,
    spend_by_category: dict[str, Decimal | float | int],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare actual needs/wants/savings vs 50/30/20 targets.

    - needs/wants: sum of mapped debit categories
    - savings: SIP/investment outflows + residual surplus
      residual = max(0, income − needs − wants − sip)
    Uncategorized "other" maps to wants (not savings).
    """
    cfg = config or load_budget_config()
    income_d = _money(income)
    cat_to_bucket: dict[str, str] = {}
    for bucket in ("needs", "wants", "savings"):
        for cat in cfg.get(bucket) or []:
            cat_to_bucket[str(cat)] = bucket

    needs = Decimal("0")
    wants = Decimal("0")
    sip = Decimal("0")
    for cat, amt in spend_by_category.items():
        amount = _money(amt)
        bucket = cat_to_bucket.get(str(cat), "wants")
        if str(cat) == "salary":
            continue
        if bucket == "needs":
            needs += amount
        elif bucket == "savings":
            sip += amount
        else:
            wants += amount

    residual = _money(max(Decimal("0"), income_d - needs - wants - sip))
    savings = _money(sip + residual)

    targets_pct = cfg.get("targets") or {"needs": 0.5, "wants": 0.3, "savings": 0.2}
    target = {
        k: _money(income_d * Decimal(str(targets_pct[k])))
        for k in ("needs", "wants", "savings")
    }
    actual = {"needs": _money(needs), "wants": _money(wants), "savings": savings}

    overshoot = []
    undershoot = []
    for bucket in ("needs", "wants", "savings"):
        diff = _money(actual[bucket] - target[bucket])
        if diff > 0:
            overshoot.append(
                {
                    "bucket": bucket,
                    "actual": actual[bucket],
                    "target": target[bucket],
                    "overshoot": diff,
                }
            )
        elif diff < 0:
            undershoot.append(
                {
                    "bucket": bucket,
                    "actual": actual[bucket],
                    "target": target[bucket],
                    "undershoot": _money(-diff),
                }
            )

    return {
        "income": income_d,
        "actual": actual,
        "target": target,
        "overshoot": overshoot,
        "undershoot": undershoot,
        "sip_outflow": _money(sip),
        "residual_surplus": residual,
        "targets_pct": {k: float(targets_pct[k]) for k in targets_pct},
    }
