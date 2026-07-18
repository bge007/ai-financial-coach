from decimal import Decimal
from pathlib import Path

from tests.conftest import login_as

FIXTURES = Path(__file__).parent / "fixtures"


def test_upload_requires_auth(client):
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()
    r = client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    )
    assert r.status_code == 401


def test_profile_requires_auth(client):
    assert client.get("/api/profile").status_code == 401


def test_upload_csv_and_get_profile(auth_client):
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()
    r = auth_client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    summary = body["summary"]
    assert summary["rows_parsed"] == 16
    assert summary["duplicate"] is False
    assert summary["date_range_start"] == "2026-01-01"
    assert summary["date_range_end"] == "2026-03-18"

    # Hand-computed (see test_profile_engine):
    # income 100000, expenses 51000, surplus 49000, emi 15000, debt 0
    profile = body["profile"]
    assert Decimal(profile["monthly_income"]) == Decimal("100000.00")
    assert Decimal(profile["monthly_expenses"]) == Decimal("51000.00")
    assert Decimal(profile["surplus"]) == Decimal("49000.00")
    assert Decimal(profile["emi_outgo"]) == Decimal("15000.00")
    assert Decimal(profile["total_debt"]) == Decimal("0.00")

    me_profile = auth_client.get("/api/profile")
    assert me_profile.status_code == 200
    assert me_profile.json()["monthly_income"] == profile["monthly_income"]


def test_duplicate_upload_adds_zero_rows(auth_client):
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()
    first = auth_client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    )
    assert first.status_code == 200
    assert first.json()["summary"]["rows_parsed"] == 16

    second = auth_client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    )
    assert second.status_code == 200
    assert second.json()["summary"]["duplicate"] is True
    assert second.json()["summary"]["rows_parsed"] == 0

    # Profile unchanged and still present.
    assert second.json()["profile"]["surplus"] == first.json()["profile"]["surplus"]


def test_upload_pdf(auth_client):
    raw = (FIXTURES / "statement_sample.pdf").read_bytes()
    r = auth_client.post(
        "/api/upload",
        files={"file": ("statement_sample.pdf", raw, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["rows_parsed"] == 16


def test_reject_oversized_file(auth_client):
    # Claim a .csv but send >10 MB
    big = b"Date,Narration,Withdrawal Amt.,Deposit Amt.\n" + b"x" * (10 * 1024 * 1024 + 1)
    r = auth_client.post(
        "/api/upload",
        files={"file": ("huge.csv", big, "text/csv")},
    )
    assert r.status_code == 400
    assert "10 MB" in r.json()["detail"]


def test_reject_unsupported_extension(auth_client):
    r = auth_client.post(
        "/api/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


def test_user_cannot_see_another_users_uploads(client, monkeypatch):
    """User A uploads; User B's profile/upload view must not include A's data."""
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()

    login_as(
        client, monkeypatch, sub="user-a", email="a@example.com", name="User A"
    )
    up = client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    )
    assert up.status_code == 200
    assert up.json()["summary"]["rows_parsed"] == 16
    a_profile = client.get("/api/profile").json()
    assert Decimal(a_profile["monthly_income"]) == Decimal("100000.00")

    # Switch to user B — empty slate.
    login_as(
        client, monkeypatch, sub="user-b", email="b@example.com", name="User B"
    )
    b_profile = client.get("/api/profile")
    assert b_profile.status_code == 200
    assert b_profile.json() is None

    # User B uploading a different file should not merge with A's rows.
    other = (FIXTURES / "sbi_sample.csv").read_bytes()
    b_up = client.post(
        "/api/upload",
        files={"file": ("sbi_sample.csv", other, "text/csv")},
    )
    assert b_up.status_code == 200
    # Same fixture shape → same profile numbers, but owned by B only.
    assert Decimal(b_up.json()["profile"]["monthly_income"]) == Decimal("100000.00")

    # Re-login as A; still only A's original data (duplicate of same hash is fine).
    login_as(
        client, monkeypatch, sub="user-a", email="a@example.com", name="User A"
    )
    again = client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    )
    assert again.json()["summary"]["duplicate"] is True
