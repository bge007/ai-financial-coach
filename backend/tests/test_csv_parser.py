from decimal import Decimal
from pathlib import Path

import pytest

from app.ingestion.csv_parser import ParseError, parse_csv
from app.models.enums import Direction

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "filename",
    ["hdfc_sample.csv", "icici_sample.csv", "sbi_sample.csv"],
)
def test_bank_csv_parses_expected_row_count(filename):
    raw = (FIXTURES / filename).read_bytes()
    txns, skipped = parse_csv(raw)
    assert len(txns) == 16
    assert skipped == 0

    credits = [t for t in txns if t.direction == Direction.credit]
    debits = [t for t in txns if t.direction == Direction.debit]
    assert len(credits) == 4  # 3 salary + 1 self-transfer credit
    assert len(debits) == 12

    salary = next(t for t in txns if "SALARY" in t.description.upper())
    assert salary.amount == Decimal("100000.00")
    assert salary.direction == Direction.credit


def test_csv_handles_rupee_commas_and_indian_grouping():
    raw = (FIXTURES / "sbi_sample.csv").read_bytes()
    txns, _ = parse_csv(raw)
    jan_salary = next(
        t for t in txns if t.date.month == 1 and "SALARY" in t.description.upper()
    )
    assert jan_salary.amount == Decimal("100000.00")


def test_empty_csv_raises():
    with pytest.raises(ParseError):
        parse_csv("not,a,bank\n1,2,3\n")
