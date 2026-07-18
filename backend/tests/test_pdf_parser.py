from decimal import Decimal
from pathlib import Path

import pytest

from app.ingestion.pdf_parser import ParseError, parse_pdf
from app.models.enums import Direction

FIXTURES = Path(__file__).parent / "fixtures"


def test_sample_pdf_parses():
    raw = (FIXTURES / "statement_sample.pdf").read_bytes()
    txns, skipped = parse_pdf(raw)
    assert len(txns) == 16
    assert skipped == 0
    credits = [t for t in txns if t.direction == Direction.credit]
    assert any(t.amount == Decimal("100000.00") for t in credits)
    assert any("EMI" in t.description.upper() for t in txns)


def test_unparseable_pdf_raises():
    # Valid-enough PDF wrapper with no transaction-shaped text.
    junk = (
        b"%PDF-1.4\n1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
        b"4 0 obj<< /Length 44 >>stream\n"
        b"BT /F1 12 Tf 50 100 Td (hello world) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"0000000266 00000 n \n0000000361 00000 n \n"
        b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n459\n%%EOF\n"
    )
    with pytest.raises(ParseError, match="Unparseable"):
        parse_pdf(junk)
