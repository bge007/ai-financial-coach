"""Debt avalanche / snowball amortization schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

TWOPLACES = Decimal("0.01")


def _money(v: Decimal | float | int) -> Decimal:
    return Decimal(str(v)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Debt:
    name: str
    principal: Decimal
    annual_rate: Decimal  # e.g. 0.12 for 12%
    min_emi: Decimal


def _add_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, d.day)
    return date(d.year, d.month + 1, min(d.day, 28))


def payoff_schedule(
    debts: list[Debt],
    extra_monthly: Decimal | float | int = 0,
    method: Literal["avalanche", "snowball"] = "avalanche",
    start: date | None = None,
) -> dict:
    """Month-by-month amortization until all debts clear.

    avalanche = highest interest first; snowball = lowest principal first.
    """
    if not debts:
        return {
            "method": method,
            "months": 0,
            "total_interest": _money(0),
            "payoff_date": None,
            "schedule": [],
        }

    balances = {d.name: _money(d.principal) for d in debts}
    rates = {d.name: Decimal(str(d.annual_rate)) for d in debts}
    emis = {d.name: _money(d.min_emi) for d in debts}
    extra = _money(extra_monthly)
    cursor = start or date.today().replace(day=1)
    total_interest = Decimal("0")
    schedule: list[dict] = []
    months = 0
    max_months = 600

    while any(v > 0 for v in balances.values()) and months < max_months:
        months += 1
        month_interest = Decimal("0")
        # Accrue interest
        for name, bal in list(balances.items()):
            if bal <= 0:
                continue
            interest = _money(bal * rates[name] / Decimal(12))
            balances[name] = _money(bal + interest)
            month_interest += interest
        total_interest += month_interest

        # Pay minimums
        paid = Decimal("0")
        for name, bal in list(balances.items()):
            if bal <= 0:
                continue
            pay = min(emis[name], bal)
            balances[name] = _money(bal - pay)
            paid += pay

        # Extra toward target debt
        remaining_extra = extra
        order = sorted(
            [n for n, b in balances.items() if b > 0],
            key=lambda n: (
                -float(rates[n]) if method == "avalanche" else float(balances[n])
            ),
        )
        for name in order:
            if remaining_extra <= 0:
                break
            bal = balances[name]
            if bal <= 0:
                continue
            pay = min(remaining_extra, bal)
            balances[name] = _money(bal - pay)
            remaining_extra -= pay
            paid += pay

        schedule.append(
            {
                "month": months,
                "date": cursor.isoformat(),
                "interest": _money(month_interest),
                "paid": _money(paid),
                "balances": {k: _money(v) for k, v in balances.items()},
            }
        )
        cursor = _add_month(cursor)

    return {
        "method": method,
        "months": months,
        "total_interest": _money(total_interest),
        "payoff_date": schedule[-1]["date"] if schedule else None,
        "schedule": schedule,
    }
