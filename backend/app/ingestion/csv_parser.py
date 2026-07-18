import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO


@dataclass(frozen=True)
class ParsedTransaction:
    date: date
    description: str
    amount: Decimal
    direction: str


@dataclass(frozen=True)
class ParseResult:
    transactions: list[ParsedTransaction]
    rows_skipped: int


DATE_HEADERS = ("date", "txn date", "transaction date", "value date", "post date")
DESC_HEADERS = (
    "description",
    "narration",
    "particulars",
    "details",
    "transaction remarks",
    "remarks",
)
DEBIT_HEADERS = ("withdrawal", "withdrawals", "debit", "debits", "withdrawal amt.")
CREDIT_HEADERS = ("deposit", "deposits", "credit", "credits", "deposit amt.")
AMOUNT_HEADERS = ("amount", "transaction amount", "amt")
TYPE_HEADERS = ("type", "dr/cr", "cr/dr", "debit/credit", "transaction type")


def parse_bank_csv(content: bytes) -> ParseResult:
    text = content.decode("utf-8-sig", errors="replace")
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV statement has no header row")

    headers = {_norm_header(h): h for h in reader.fieldnames if h is not None}
    date_key = _find_header(headers, DATE_HEADERS)
    desc_key = _find_header(headers, DESC_HEADERS)
    debit_key = _find_header(headers, DEBIT_HEADERS)
    credit_key = _find_header(headers, CREDIT_HEADERS)
    amount_key = _find_header(headers, AMOUNT_HEADERS)
    type_key = _find_header(headers, TYPE_HEADERS)

    if not date_key or not desc_key:
        raise ValueError("CSV statement must include date and description columns")
    if not ((debit_key and credit_key) or amount_key):
        raise ValueError("CSV statement must include debit/credit or amount columns")

    transactions: list[ParsedTransaction] = []
    skipped = 0
    for row in reader:
        try:
            txn_date = _parse_date(row.get(date_key, ""))
            description = " ".join((row.get(desc_key) or "").split())
            if not description:
                raise ValueError("missing description")
            amount, direction = _extract_amount_direction(
                row, debit_key, credit_key, amount_key, type_key
            )
            if amount <= 0:
                raise ValueError("non-positive amount")
            transactions.append(
                ParsedTransaction(
                    date=txn_date,
                    description=description,
                    amount=amount.quantize(Decimal("0.01")),
                    direction=direction,
                )
            )
        except ValueError:
            skipped += 1

    if not transactions:
        raise ValueError("CSV statement did not contain any parseable transactions")
    return ParseResult(transactions=transactions, rows_skipped=skipped)


def parse_statement_lines(lines: list[str]) -> ParseResult:
    transactions: list[ParsedTransaction] = []
    skipped = 0
    pattern = re.compile(
        r"^(?P<date>\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<amount>(?:₹|Rs\.?)?\s*[\d,]+(?:\.\d{1,2})?)\s+"
        r"(?P<direction>debit|credit|dr|cr)\b",
        re.IGNORECASE,
    )
    for line in lines:
        match = pattern.search(" ".join(line.split()))
        if not match:
            skipped += 1
            continue
        try:
            direction_token = match.group("direction").lower()
            transactions.append(
                ParsedTransaction(
                    date=_parse_date(match.group("date")),
                    description=match.group("desc").strip(),
                    amount=_parse_amount(match.group("amount")).quantize(Decimal("0.01")),
                    direction="credit" if direction_token in {"credit", "cr"} else "debit",
                )
            )
        except ValueError:
            skipped += 1
    return ParseResult(transactions=transactions, rows_skipped=skipped)


def _find_header(headers: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in headers:
            return headers[candidate]
    for normalized, original in headers.items():
        if any(candidate in normalized for candidate in candidates):
            return original
    return None


def _norm_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _parse_date(value: str) -> date:
    cleaned = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"invalid date: {value}")


def _parse_amount(value: str | None) -> Decimal:
    cleaned = (value or "").strip()
    if not cleaned or cleaned in {"-", "--"}:
        return Decimal("0")
    cleaned = (
        cleaned.replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace(",", "")
        .strip()
    )
    cleaned = re.sub(r"\s*(dr|cr)$", "", cleaned, flags=re.IGNORECASE)
    try:
        return abs(Decimal(cleaned))
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {value}") from exc


def _extract_amount_direction(
    row: dict[str, str],
    debit_key: str | None,
    credit_key: str | None,
    amount_key: str | None,
    type_key: str | None,
) -> tuple[Decimal, str]:
    if debit_key and credit_key:
        debit = _parse_amount(row.get(debit_key))
        credit = _parse_amount(row.get(credit_key))
        if debit > 0 and credit == 0:
            return debit, "debit"
        if credit > 0 and debit == 0:
            return credit, "credit"
        raise ValueError("row must have exactly one debit or credit amount")

    amount_text = row.get(amount_key or "", "")
    amount = _parse_amount(amount_text)
    type_text = (row.get(type_key or "", "") + " " + amount_text).lower()
    if any(token in type_text for token in ("credit", " cr", "cr")):
        return amount, "credit"
    if any(token in type_text for token in ("debit", " dr", "dr")):
        return amount, "debit"
    if str(amount_text).strip().startswith("-"):
        return amount, "debit"
    return amount, "credit"
