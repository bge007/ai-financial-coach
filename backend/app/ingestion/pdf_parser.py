"""PDF statement parser: table extraction first, line-regex fallback."""

from __future__ import annotations

import io
import re
from decimal import Decimal

import pdfplumber

from app.ingestion.csv_parser import ParseError
from app.ingestion.normalize import parse_amount, parse_indian_date
from app.models.enums import Direction
from app.models.schemas import ParsedTransaction

# Date + description + optional debit/credit amounts on one line.
_LINE_RE = re.compile(
    r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+"
    r"(?P<desc>.+?)\s+"
    r"(?P<a1>₹?[\d,]+\.\d{2})\s*"
    r"(?P<a2>₹?[\d,]+\.\d{2})?",
    re.IGNORECASE,
)


def _txn_from_cells(
    date_raw: str,
    desc: str,
    debit_raw: str | None,
    credit_raw: str | None,
) -> ParsedTransaction | None:
    txn_date = parse_indian_date(date_raw)
    if txn_date is None:
        return None
    debit = parse_amount(debit_raw) if debit_raw else None
    credit = parse_amount(credit_raw) if credit_raw else None
    if debit and not credit:
        return ParsedTransaction(
            date=txn_date,
            description=(desc or "Unknown").strip(),
            amount=debit,
            direction=Direction.debit,
        )
    if credit and not debit:
        return ParsedTransaction(
            date=txn_date,
            description=(desc or "Unknown").strip(),
            amount=credit,
            direction=Direction.credit,
        )
    return None


def _parse_tables(pdf: pdfplumber.PDF) -> list[ParsedTransaction]:
    transactions: list[ParsedTransaction] = []
    for page in pdf.pages:
        tables = page.extract_tables() or []
        for table in tables:
            if not table or len(table) < 2:
                continue
            header = [((c or "").strip().lower()) for c in table[0]]
            # Locate columns by fuzzy header match.
            date_i = desc_i = debit_i = credit_i = None
            for i, h in enumerate(header):
                if date_i is None and "date" in h:
                    date_i = i
                elif desc_i is None and any(
                    k in h for k in ("narration", "particular", "description", "remark")
                ):
                    desc_i = i
                elif debit_i is None and any(
                    k in h for k in ("withdraw", "debit", "dr")
                ):
                    debit_i = i
                elif credit_i is None and any(
                    k in h for k in ("deposit", "credit", "cr")
                ):
                    credit_i = i
            if date_i is None or desc_i is None:
                continue
            for row in table[1:]:
                if not row or date_i >= len(row):
                    continue
                debit_raw = row[debit_i] if debit_i is not None and debit_i < len(row) else None
                credit_raw = (
                    row[credit_i] if credit_i is not None and credit_i < len(row) else None
                )
                txn = _txn_from_cells(
                    str(row[date_i] or ""),
                    str(row[desc_i] or ""),
                    str(debit_raw) if debit_raw else None,
                    str(credit_raw) if credit_raw else None,
                )
                if txn:
                    transactions.append(txn)
    return transactions


def _parse_lines(text: str) -> tuple[list[ParsedTransaction], int]:
    transactions: list[ParsedTransaction] = []
    skipped = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _LINE_RE.search(line)
        if not m:
            # Count only lines that look like they might be txn rows.
            if re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", line):
                skipped += 1
            continue
        a1 = parse_amount(m.group("a1"))
        a2 = parse_amount(m.group("a2")) if m.group("a2") else None
        desc = m.group("desc").strip()
        desc_upper = desc.upper()
        # Heuristic: salary/credit keywords → credit; else if two amounts,
        # treat first as debit and second as credit (one should be empty in
        # well-formed lines — when both present prefer credit keywords).
        if a2 and not a1:
            direction = Direction.credit
            amount = a2
        elif a1 and not a2:
            if any(k in desc_upper for k in ("SALARY", "CREDIT", "INTEREST", "REFUND")):
                direction = Direction.credit
            else:
                direction = Direction.debit
            amount = a1
        elif a1 and a2:
            # Two amounts: non-zero "withdrawal" style — use the larger as the
            # txn amount with keyword-based direction (balance often trails).
            # Prefer credit keywords; otherwise debit.
            if any(k in desc_upper for k in ("SALARY", "CREDIT", "INTEREST", "REFUND")):
                direction = Direction.credit
                amount = a2 if a2 >= a1 else a1
            else:
                direction = Direction.debit
                amount = a1
        else:
            skipped += 1
            continue

        txn_date = parse_indian_date(m.group("date"))
        if txn_date is None or amount is None:
            skipped += 1
            continue
        transactions.append(
            ParsedTransaction(
                date=txn_date,
                description=desc,
                amount=Decimal(amount),
                direction=direction,
            )
        )
    return transactions, skipped


def parse_pdf(content: bytes) -> tuple[list[ParsedTransaction], int]:
    """Parse a statement PDF.

    Returns (transactions, rows_skipped).
    Raises ParseError when the file yields no usable rows.
    """
    if not content:
        raise ParseError("PDF file is empty")

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            table_txns = _parse_tables(pdf)
            if table_txns:
                return table_txns, 0

            text_parts = [(page.extract_text() or "") for page in pdf.pages]
            text = "\n".join(text_parts)
    except Exception as exc:  # pdfplumber / pdfminer failures
        raise ParseError(f"Unparseable PDF statement: {exc}") from exc

    if not text.strip():
        raise ParseError("Unparseable PDF statement: no extractable text")

    transactions, skipped = _parse_lines(text)
    if not transactions:
        raise ParseError(
            "Unparseable PDF statement: could not extract transaction rows"
        )
    return transactions, skipped
