"""Guardrail: every ₹ figure in prose must appear in figures_used / engine figures."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from app.agents.llm import DISCLAIMER, AgentOutput

# Match ₹1,50,000 or 150000.00 or 1,50,000 style amounts.
_RUPEE_RE = re.compile(
    r"(?:₹\s*)?((?:\d{1,3}(?:,\d{2})*(?:,\d{3})+)|\d+)(?:\.(\d{1,2}))?",
)


def _normalize_amount(raw: str) -> str:
    return raw.replace(",", "").replace("₹", "").strip()


def _canon_amount(raw: str) -> str | None:
    """Canonical money key: always two-decimal string when parseable."""
    text = _normalize_amount(raw)
    if not text:
        return None
    try:
        return f"{Decimal(text).quantize(Decimal('0.01')):.2f}"
    except (InvalidOperation, ValueError):
        return None


def _expand_allowed(values: Iterable[str]) -> set[str]:
    """Accept both 40000 and 40000.00 style citations."""
    allowed: set[str] = set()
    for v in values:
        raw = _normalize_amount(str(v))
        if not raw:
            continue
        allowed.add(raw)
        canon = _canon_amount(raw)
        if canon:
            allowed.add(canon)
            # Also allow integer form without trailing .00
            if canon.endswith(".00"):
                allowed.add(canon[:-3])
        # Percentage helpers: 0.28 → 28 / 28.00
        try:
            d = Decimal(raw)
            if Decimal("0") < d <= Decimal("1"):
                pct = (d * 100).quantize(Decimal("0.01"))
                allowed.add(f"{pct:.2f}")
                if pct == pct.to_integral_value():
                    allowed.add(str(int(pct)))
        except (InvalidOperation, ValueError):
            pass
    return allowed


def extract_rupee_figures(text: str) -> list[str]:
    found: list[str] = []
    for m in _RUPEE_RE.finditer(text or ""):
        whole = m.group(0)
        # Skip bare years / small ints without ₹ when not looking money-like
        if "₹" not in whole and "," not in whole and "." not in whole:
            # Require ₹ or Indian grouping or decimals for bare digits > 3 chars
            num = _normalize_amount(m.group(1))
            if len(num) < 4:
                continue
        norm = _normalize_amount(m.group(1) + (("." + m.group(2)) if m.group(2) else ""))
        if norm and norm not in found:
            found.append(norm)
    return found


def apply_guardrail(
    output: AgentOutput,
    *,
    financial_year: str = "2026-27",
    allowed_figures: list[str] | None = None,
) -> dict[str, Any]:
    # Engine context figures are the source of truth; figures_used is a hint.
    seed = list(output.figures_used or [])
    if allowed_figures:
        seed.extend(allowed_figures)
    allowed = _expand_allowed(seed)
    prose_nums = extract_rupee_figures(output.summary)
    for rec in output.recommendations:
        prose_nums.extend(extract_rupee_figures(rec))

    invented: list[str] = []
    for n in prose_nums:
        canon = _canon_amount(n) or _normalize_amount(n)
        if canon not in allowed and _normalize_amount(n) not in allowed:
            invented.append(n)

    summary = output.summary
    recommendations = list(output.recommendations)
    flagged = False
    if invented:
        flagged = True
        # Longest first so "40000" is not partially eaten by a shorter invented token.
        for n in sorted(set(invented), key=len, reverse=True):
            # Match whole money tokens only (avoid turning "28%" into "[amount withheld]8%").
            # Allow a trailing sentence "." — only block more digits (not "[\d.]").
            pat = re.compile(
                rf"(?<![\d.])₹?\s*{re.escape(n)}(?!\d)",
            )
            summary = pat.sub("[amount withheld]", summary)
            recommendations = [pat.sub("[amount withheld]", r) for r in recommendations]
        summary += (
            " Note: some figures were withheld because they were not produced "
            "by the finance engines."
        )

    if DISCLAIMER not in summary:
        summary = summary.rstrip() + f"\n\n{DISCLAIMER}"
    fy_stamp = f"Figures refer to FY {financial_year}."
    if fy_stamp not in summary:
        summary = summary.rstrip() + f"\n{fy_stamp}"

    return {
        "summary": summary,
        "recommendations": recommendations,
        "figures_used": list(output.figures_used),
        "flagged_invented_numbers": invented,
        "guardrail_flagged": flagged,
        "disclaimer": DISCLAIMER,
        "financial_year": financial_year,
    }
