"""Shared normalization helpers for Indian bank statement parsers."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Common Indian date formats seen in HDFC / ICICI / SBI exports.
_DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d.%m.%y",
    "%Y-%m-%d",
    "%d %b %Y",
    "%d-%b-%Y",
    "%d %B %Y",
)

_AMOUNT_RE = re.compile(r"[^\d.\-]")


def parse_indian_date(raw: str) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(raw: str | int | float | None) -> Decimal | None:
    """Parse amounts that may include ₹, commas, or surrounding whitespace."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        try:
            value = Decimal(str(raw))
        except InvalidOperation:
            return None
        return abs(value) if value != 0 else None

    text = str(raw).strip()
    if not text or text in {"-", "--", "NA", "N/A"}:
        return None
    text = text.replace("₹", "").replace(",", "").replace(" ", "")
    text = _AMOUNT_RE.sub("", text)
    if not text or text in {".", "-", "-."}:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    if value == 0:
        return None
    return abs(value)


def normalize_header(name: str) -> str:
    """Lowercase, strip parentheticals / punctuation, collapse whitespace."""
    text = (name or "").strip().lower()
    text = re.sub(r"\([^)]*\)", " ", text)  # drop (INR), etc.
    text = text.replace(".", " ").replace("/", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text
