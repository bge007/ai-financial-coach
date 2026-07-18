from datetime import date
from decimal import Decimal

from app.api import auth as auth_api
from app.core.auth import COOKIE_NAME
from app.engines.profile import derive_profile_numbers
from app.ingestion.csv_parser import parse_bank_csv
from app.ingestion.pdf_parser import parse_bank_pdf
from app.models.finance import Transaction


HDFC_CSV = """Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance
01/04/2026,SALARY ACME,,"₹1,50,000.00","₹1,50,000.00"
02/04/2026,RENT PAYMENT,"45,000.00",,"₹1,05,000.00"
05/04/2026,HOME LOAN EMI,"20,000.00",,"₹85,000.00"
01/05/2026,SALARY ACME,,"₹1,60,000.00","₹2,45,000.00"
02/05/2026,RENT PAYMENT,"50,000.00",,"₹1,95,000.00"
05/05/2026,HOME LOAN EMI,"20,000.00",,"₹1,75,000.00"
"""

ICICI_CSV = """Transaction Date,Transaction Remarks,Debit,Credit,Balance
03-04-2026,UPI GROCERIES,5000,,95000
07-04-2026,BONUS,,10000,105000
"""

SBI_CSV = """Txn Date,Description,Amount,Dr/Cr,Balance
08/04/26,ATM CASH,2000,DR,103000
09/04/26,INTEREST,100,CR,103100
"""


def test_csv_parser_handles_common_indian_bank_formats():
    hdfc = parse_bank_csv(HDFC_CSV.encode())
    icici = parse_bank_csv(ICICI_CSV.encode())
    sbi = parse_bank_csv(SBI_CSV.encode())

    assert len(hdfc.transactions) == 6
    assert hdfc.transactions[0].amount == Decimal("150000.00")
    assert hdfc.transactions[0].direction == "credit"
    assert icici.transactions[0].description == "UPI GROCERIES"
    assert icici.transactions[0].direction == "debit"
    assert sbi.transactions[1].direction == "credit"
    assert sbi.transactions[1].amount == Decimal("100.00")


def test_pdf_parser_extracts_statement_lines():
    pdf = _minimal_pdf(
        "01/04/2026 SALARY ACME 150000.00 Credit\n"
        "02/04/2026 RENT PAYMENT 45000.00 Debit\n"
    )
    result = parse_bank_pdf(pdf)

    assert len(result.transactions) == 2
    assert result.transactions[0].description == "SALARY ACME"
    assert result.transactions[1].amount == Decimal("45000.00")


def test_profile_numbers_match_hand_computed_fixture():
    transactions = [
        _txn("2026-04-01", "SALARY ACME", "150000.00", "credit"),
        _txn("2026-04-02", "RENT PAYMENT", "45000.00", "debit"),
        _txn("2026-04-05", "HOME LOAN EMI", "20000.00", "debit"),
        _txn("2026-05-01", "SALARY ACME", "160000.00", "credit"),
        _txn("2026-05-02", "RENT PAYMENT", "50000.00", "debit"),
        _txn("2026-05-05", "HOME LOAN EMI", "20000.00", "debit"),
        _txn("2026-05-06", "SELF TRANSFER FROM OWN ACCOUNT", "40000.00", "credit"),
    ]

    profile = derive_profile_numbers(transactions)

    # Income median: (150000 + 160000) / 2 = 155000.
    assert profile.monthly_income == Decimal("155000.00")
    # Expense median: ((45000 + 20000) + (50000 + 20000)) / 2 = 67500.
    assert profile.monthly_expenses == Decimal("67500.00")
    assert profile.surplus == Decimal("87500.00")
    assert profile.emi_outgo == Decimal("20000.00")
    assert profile.total_debt == Decimal("0.00")


def test_profile_numbers_are_zero_without_transactions():
    profile = derive_profile_numbers([])

    assert profile.monthly_income == Decimal("0.00")
    assert profile.monthly_expenses == Decimal("0.00")
    assert profile.surplus == Decimal("0.00")
    assert profile.emi_outgo == Decimal("0.00")
    assert profile.total_debt == Decimal("0.00")


def test_upload_is_idempotent_and_profile_is_returned(client, monkeypatch):
    _login_as(client, monkeypatch, "user-upload", "upload@example.com")

    first = client.post(
        "/api/upload",
        files={"file": ("hdfc.csv", HDFC_CSV, "text/csv")},
    )
    assert first.status_code == 200
    assert first.json()["rows_added"] == 6
    assert first.json()["date_range"] == {"from": "2026-04-01", "to": "2026-05-05"}

    second = client.post(
        "/api/upload",
        files={"file": ("hdfc.csv", HDFC_CSV, "text/csv")},
    )
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["rows_added"] == 0

    profile = client.get("/api/profile")
    assert profile.status_code == 200
    assert profile.json()["monthly_income"] == "155000.00"
    assert profile.json()["monthly_expenses"] == "67500.00"
    assert profile.json()["surplus"] == "87500.00"
    assert profile.json()["emi_outgo"] == "20000.00"
    assert profile.json()["transactions_count"] == 6


def test_user_cannot_see_another_users_uploads(client, monkeypatch):
    _login_as(client, monkeypatch, "phase1-user-a", "phase1-a@example.com")
    assert (
        client.post(
            "/api/upload",
            files={"file": ("hdfc.csv", HDFC_CSV, "text/csv")},
        ).status_code
        == 200
    )

    _login_as(client, monkeypatch, "phase1-user-b", "phase1-b@example.com")
    profile = client.get("/api/profile")
    assert profile.status_code == 200
    assert profile.json()["transactions_count"] == 0
    assert profile.json()["monthly_income"] == "0.00"


def _txn(date_text: str, description: str, amount: str, direction: str) -> Transaction:
    return Transaction(
        user_id=1,
        date=date.fromisoformat(date_text),
        description=description,
        amount=Decimal(amount),
        direction=direction,
        source_file="fixture.csv",
        uploaded_file_id=1,
    )


def _login_as(client, monkeypatch, google_sub: str, email: str) -> None:
    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": google_sub, "email": email, "name": email}}

    monkeypatch.setattr(
        auth_api.oauth.google, "authorize_access_token", fake_authorize_access_token
    )
    response = client.get("/auth/callback", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert COOKIE_NAME in response.headers.get("set-cookie", "")


def _minimal_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = escaped.splitlines()
    text_ops = ["BT", "/F1 12 Tf", "72 740 Td"]
    for index, line in enumerate(lines):
        if index:
            text_ops.append("0 -18 Td")
        text_ops.append(f"({line}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
