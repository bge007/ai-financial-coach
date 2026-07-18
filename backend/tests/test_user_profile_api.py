"""User-entered profile preferences API."""

from decimal import Decimal

from tests.conftest import login_as


def test_user_profile_requires_auth(client):
    assert client.get("/api/user-profile").status_code == 401
    assert client.put("/api/user-profile", json={}).status_code == 401


def test_user_profile_put_get(auth_client):
    empty = auth_client.get("/api/user-profile")
    assert empty.status_code == 200
    assert empty.json() is None

    saved = auth_client.put(
        "/api/user-profile",
        json={
            "name": "Priya Sharma",
            "age": 32,
            "city": "Bengaluru",
            "monthly_income": "150000.00",
            "emergency_fund": "300000.00",
            "risk_profile": "moderate",
        },
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["name"] == "Priya Sharma"
    assert body["age"] == 32
    assert body["city"] == "Bengaluru"
    assert Decimal(body["monthly_income"]) == Decimal("150000.00")
    assert Decimal(body["emergency_fund"]) == Decimal("300000.00")
    assert body["risk_profile"] == "moderate"

    loaded = auth_client.get("/api/user-profile")
    assert loaded.status_code == 200
    assert loaded.json()["name"] == "Priya Sharma"


def test_user_profile_rejects_bad_risk(auth_client):
    r = auth_client.put(
        "/api/user-profile",
        json={"name": "X", "risk_profile": "yolo"},
    )
    assert r.status_code == 422


def test_user_profile_isolation(client, monkeypatch):
    login_as(client, monkeypatch, sub="upa", email="upa@example.com", name="A")
    client.put(
        "/api/user-profile",
        json={"name": "User A", "city": "Mumbai", "risk_profile": "aggressive"},
    )
    assert client.get("/api/user-profile").json()["name"] == "User A"

    login_as(client, monkeypatch, sub="upb", email="upb@example.com", name="B")
    assert client.get("/api/user-profile").json() is None
    client.put(
        "/api/user-profile",
        json={"name": "User B", "city": "Delhi", "risk_profile": "conservative"},
    )
    assert client.get("/api/user-profile").json()["name"] == "User B"

    login_as(client, monkeypatch, sub="upa", email="upa@example.com", name="A")
    assert client.get("/api/user-profile").json()["name"] == "User A"
