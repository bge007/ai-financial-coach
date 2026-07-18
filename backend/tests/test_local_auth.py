"""Email/password signup and login — AUTH_DISABLED stays false via conftest."""

from datetime import date

from app.core.auth import COOKIE_NAME


def _signup_payload(**overrides):
    payload = {
        "name": "Priya Sharma",
        "email": "priya@example.com",
        "dob": "1994-05-12",
        "gender": "female",
        "password": "securePass1",
        "confirm_password": "securePass1",
    }
    payload.update(overrides)
    return payload


def test_signup_sets_cookie_and_me(client):
    r = client.post("/auth/signup", json=_signup_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "priya@example.com"
    assert body["name"] == "Priya Sharma"
    assert body["gender"] == "female"
    assert COOKIE_NAME in r.cookies

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]
    assert me.json()["email"] == "priya@example.com"


def test_signup_seeds_user_profile(client):
    r = client.post("/auth/signup", json=_signup_payload())
    assert r.status_code == 201
    profile = client.get("/api/user-profile")
    assert profile.status_code == 200
    body = profile.json()
    assert body["name"] == "Priya Sharma"
    # Age from DOB 1994-05-12 relative to "today" — just assert it's present and sane.
    assert body["age"] is not None
    assert 18 <= body["age"] <= 100


def test_signup_duplicate_email_rejected(client):
    assert client.post("/auth/signup", json=_signup_payload()).status_code == 201
    r = client.post("/auth/signup", json=_signup_payload(name="Other"))
    assert r.status_code == 409


def test_signup_password_mismatch(client):
    r = client.post(
        "/auth/signup",
        json=_signup_payload(confirm_password="differentPass1"),
    )
    assert r.status_code == 422


def test_signup_short_password(client):
    r = client.post(
        "/auth/signup",
        json=_signup_payload(password="short", confirm_password="short"),
    )
    assert r.status_code == 422


def test_login_success(client):
    client.post("/auth/signup", json=_signup_payload())
    client.cookies.clear()
    r = client.post(
        "/auth/login",
        json={"email": "priya@example.com", "password": "securePass1"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "priya@example.com"
    assert COOKIE_NAME in r.cookies
    assert client.get("/auth/me").status_code == 200


def test_login_wrong_password(client):
    client.post("/auth/signup", json=_signup_payload())
    client.cookies.clear()
    r = client.post(
        "/auth/login",
        json={"email": "priya@example.com", "password": "wrongPass99"},
    )
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "securePass1"},
    )
    assert r.status_code == 401


def test_login_rejects_google_only_user(client, monkeypatch):
    from app.api import auth as auth_api

    async def fake_authorize_access_token(request):
        return {
            "userinfo": {
                "sub": "google-only-1",
                "email": "googleonly@example.com",
                "name": "G Only",
            }
        }

    monkeypatch.setattr(
        auth_api.oauth.google, "authorize_access_token", fake_authorize_access_token
    )
    client.get("/auth/callback", follow_redirects=False)
    client.cookies.clear()

    r = client.post(
        "/auth/login",
        json={"email": "googleonly@example.com", "password": "anything12"},
    )
    assert r.status_code == 401
    assert "password" in r.json()["detail"].lower()


def test_logout_clears_local_session(client):
    client.post("/auth/signup", json=_signup_payload())
    assert client.get("/auth/me").status_code == 200
    out = client.post("/auth/logout")
    assert out.status_code == 200
    # Cookie deleted; subsequent me should 401
    client.cookies.clear()
    assert client.get("/auth/me").status_code == 401


def test_users_isolated_by_user_id(client):
    a = client.post("/auth/signup", json=_signup_payload(email="a@example.com"))
    assert a.status_code == 201
    id_a = a.json()["id"]
    client.cookies.clear()

    b = client.post(
        "/auth/signup",
        json=_signup_payload(
            email="b@example.com",
            name="B User",
            dob=str(date(1990, 1, 1)),
        ),
    )
    assert b.status_code == 201
    id_b = b.json()["id"]
    assert id_a != id_b
    me = client.get("/auth/me").json()
    assert me["id"] == id_b
    assert me["email"] == "b@example.com"
