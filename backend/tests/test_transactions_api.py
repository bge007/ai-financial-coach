"""Transaction API: list filters, recategorize, isolation."""

from pathlib import Path

from tests.conftest import login_as

FIXTURES = Path(__file__).parent / "fixtures"


def test_transactions_require_auth(client):
    assert client.get("/api/transactions").status_code == 401


def test_list_and_filter_transactions(auth_client):
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()
    assert auth_client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    ).status_code == 200

    all_rows = auth_client.get("/api/transactions")
    assert all_rows.status_code == 200
    body = all_rows.json()
    assert body["total"] == 16
    assert len(body["items"]) == 16
    assert all(item["category"] is not None for item in body["items"])

    jan = auth_client.get("/api/transactions?month=2026-01")
    assert jan.status_code == 200
    assert jan.json()["total"] == 6

    dining = auth_client.get("/api/transactions?category=dining")
    assert dining.status_code == 200
    assert dining.json()["total"] >= 1

    search = auth_client.get("/api/transactions?search=EMI")
    assert search.status_code == 200
    assert search.json()["total"] >= 1


def test_recategorize_404_for_other_user(client, monkeypatch):
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()
    login_as(client, monkeypatch, sub="user-a", email="a@example.com", name="A")
    up = client.post(
        "/api/upload",
        files={"file": ("hdfc_sample.csv", raw, "text/csv")},
    )
    assert up.status_code == 200
    txn_id = client.get("/api/transactions").json()["items"][0]["id"]

    login_as(client, monkeypatch, sub="user-b", email="b@example.com", name="B")
    r = client.post(
        f"/api/transactions/{txn_id}/recategorize",
        json={"category": "other"},
    )
    assert r.status_code == 404

    empty = client.get("/api/transactions")
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
