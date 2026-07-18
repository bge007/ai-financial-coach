"""Tolerant CSV parser for common Indian bank layouts (HDFC / ICICI / SBI).

Column aliases are data-driven so new bank variants can be added without
special-case code branches.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from app.ingestion.normalize import normalize_header, parse_amount, parse_indian_date
from app.models.enums import Direction
from app.models.schemas import ParsedTransaction

# Maps normalized header → logical field. Multiple aliases per field.
_HEADER_ALIASES: dict[str, str] = {
    # date
    "date": "date",
    "txn date": "date",
    "transaction date": "date",
    "value date": "date",
    "tran date": "date",
    "posting date": "date",
    # description
    "narration": "description",
    "description": "description",
    "particulars": "description",
    "transaction remarks": "description",
    "remarks": "description",
    "details": "description",
    # withdrawal / debit
    "withdrawal amt": "debit",
    "withdrawal amount": "debit",
    "withdrawal": "debit",
    "debit": "debit",
    "debit amount": "debit",
    "withdrawals": "debit",
    "dr": "debit",
    "dr amount": "debit",
    # deposit / credit
    "deposit amt": "deposit",
    "deposit amount": "deposit",
    "deposit": "deposit",
    "credit": "deposit",
    "credit amount": "deposit",
    "deposits": "deposit",
    "cr": "deposit",
    "cr amount": "deposit",
    # amount + type variants
    "amount": "amount",
    "txn amount": "amount",
    "transaction amount": "amount",
    "type": "txn_type",
    "cr dr": "txn_type",
    "dr cr": "txn_type",
    "transaction type": "txn_type",
}


class ParseError(ValueError):
    """Raised when a statement cannot be interpreted."""


def _detect_header_row(rows: list[list[str]]) -> tuple[int, dict[str, int]]:
    """Find the first row that looks like a bank-statement header."""
    for idx, row in enumerate(rows[:30]):
        mapping: dict[str, int] = {}
        for col_i, cell in enumerate(row):
            key = normalize_header(cell)
            field = _HEADER_ALIASES.get(key)
            if field and field not in mapping:
                mapping[field] = col_i
        has_date = "date" in mapping
        has_desc = "description" in mapping
        has_money = (
            ("debit" in mapping and "deposit" in mapping)
            or ("amount" in mapping)
        )
        if has_date and has_desc and has_money:
            return idx, mapping
    raise ParseError(
        "Could not detect a bank-statement header row "
        "(expected date, narration/description, and debit/credit columns)"
    )


def _direction_from_type(raw: str) -> Direction | None:
    text = (raw or "").strip().lower()
    if not text:
        return None
    if text in {"dr", "debit", "withdrawal", "w", "d"}:
        return Direction.debit
    if text in {"cr", "credit", "deposit", "c"}:
        return Direction.credit
    if "debit" in text or "withdraw" in text:
        return Direction.debit
    if "credit" in text or "deposit" in text:
        return Direction.credit
    return None


def _row_to_txn(row: list[str], mapping: dict[str, int]) -> ParsedTransaction | None:
    def cell(field: str) -> str:
        i = mapping.get(field)
        if i is None or i >= len(row):
            return ""
        return (row[i] or "").strip()

    txn_date = parse_indian_date(cell("date"))
    if txn_date is None:
        return None

    description = cell("description") or "Unknown"
    debit = parse_amount(cell("debit")) if "debit" in mapping else None
    deposit = parse_amount(cell("deposit")) if "deposit" in mapping else None

    if debit and deposit:
        # Prefer the non-empty side; skip ambiguous rows.
        return None
    if debit:
        return ParsedTransaction(
            date=txn_date,
            description=description,
            amount=debit,
            direction=Direction.debit,
        )
    if deposit:
        return ParsedTransaction(
            date=txn_date,
            description=description,
            amount=deposit,
            direction=Direction.credit,
        )

    amount = parse_amount(cell("amount")) if "amount" in mapping else None
    if amount is None:
        return None
    direction = _direction_from_type(cell("txn_type"))
    if direction is None:
        # Signed amount fallback: negative → debit.
        raw_amt = cell("amount").replace(",", "").replace("₹", "").strip()
        if raw_amt.startswith("-"):
            direction = Direction.debit
        else:
            return None
    return ParsedTransaction(
        date=txn_date,
        description=description,
        amount=amount,
        direction=direction,
    )


def parse_csv(content: bytes | str) -> tuple[list[ParsedTransaction], int]:
    """Parse CSV bytes/text into normalized transactions.

    Returns (transactions, rows_skipped).
    """
    if isinstance(content, bytes):
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content

    # Sniff delimiter; fall back to comma.
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t|;")
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(text), dialect)
    rows = [list(r) for r in reader if any((c or "").strip() for c in r)]
    if not rows:
        raise ParseError("CSV file is empty")

    header_idx, mapping = _detect_header_row(rows)
    transactions: list[ParsedTransaction] = []
    skipped = 0
    for row in rows[header_idx + 1 :]:
        # Stop at trailing bank summary / empty blocks.
        if not any((c or "").strip() for c in row):
            continue
        first = normalize_header(row[0]) if row else ""
        if first.startswith("*") or first.startswith("statement summary"):
            break
        txn = _row_to_txn(row, mapping)
        if txn is None:
            skipped += 1
            continue
        transactions.append(txn)

    if not transactions:
        raise ParseError("No parseable transactions found in CSV")
    return transactions, skipped


def parse_csv_dict_rows(rows: list[dict[str, Any]]) -> tuple[list[ParsedTransaction], int]:
    """Convenience for tests that build dict rows instead of raw CSV text."""
    if not rows:
        raise ParseError("CSV file is empty")
    headers = list(rows[0].keys())
    lines = [headers] + [[str(r.get(h, "")) for h in headers] for r in rows]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerows(lines)
    return parse_csv(buf.getvalue())
