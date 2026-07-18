"""Isolation audit + account data deletion."""

from pathlib import Path

from tests.conftest import login_as

FIXTURES = Path(__file__).parent / "fixtures"


def test_isolation_audit_across_data_endpoints(client, monkeypatch):
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()
    login_as(client, monkeypatch, sub="iso-a", email="iso-a@example.com", name="A")
    assert client.post(
        "/api/upload", files={"file": ("hdfc.csv", raw, "text/csv")}
    ).status_code == 200
    txn_id = client.get("/api/transactions").json()["items"][0]["id"]
    assert client.get("/api/profile").json() is not None
    assert client.get("/api/dashboard").status_code == 200
    assert client.get("/api/analytics").status_code == 200

    login_as(client, monkeypatch, sub="iso-b", email="iso-b@example.com", name="B")
    assert client.get("/api/profile").json() is None
    assert client.get("/api/transactions").json()["total"] == 0
    assert client.get("/api/dashboard").json()["profile"] is None
    assert (
        client.post(
            f"/api/transactions/{txn_id}/recategorize",
            json={"category": "other"},
        ).status_code
        == 404
    )


def test_delete_my_data_leaves_zero_rows(client, monkeypatch):
    raw = (FIXTURES / "hdfc_sample.csv").read_bytes()
    login_as(client, monkeypatch, sub="del-a", email="del-a@example.com", name="D")
    assert client.post(
        "/api/upload", files={"file": ("hdfc.csv", raw, "text/csv")}
    ).status_code == 200
    assert client.get("/api/transactions").json()["total"] == 16

    deleted = client.delete("/api/me/data")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert deleted.json()["residual_transactions"] is False
    assert client.get("/api/transactions").json()["total"] == 0
    assert client.get("/api/profile").json() is None
