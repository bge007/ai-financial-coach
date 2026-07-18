"""Guardrail: every ₹ figure in prose must appear in figures_used."""

from __future__ import annotations

import re
from typing import Any

from app.agents.llm import DISCLAIMER, AgentOutput

# Match ₹1,50,000 or 150000.00 or 1,50,000 style amounts.
_RUPEE_RE = re.compile(
    r"(?:₹\s*)?((?:\d{1,3}(?:,\d{2})*(?:,\d{3})+)|\d+)(?:\.(\d{1,2}))?",
)


def _normalize_amount(raw: str) -> str:
    return raw.replace(",", "").replace("₹", "").strip()


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
) -> dict[str, Any]:
    allowed = {_normalize_amount(x) for x in output.figures_used}
    prose_nums = extract_rupee_figures(output.summary)
    for rec in output.recommendations:
        prose_nums.extend(extract_rupee_figures(rec))

    invented = [n for n in prose_nums if n not in allowed]
    summary = output.summary
    recommendations = list(output.recommendations)
    flagged = False
    if invented:
        flagged = True
        # Strip invented numbers from summary by replacing with [amount withheld]
        for n in invented:
            summary = re.sub(
                rf"₹?\s*{re.escape(n)}",
                "[amount withheld]",
                summary,
            )
            recommendations = [
                re.sub(rf"₹?\s*{re.escape(n)}", "[amount withheld]", r)
                for r in recommendations
            ]
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
