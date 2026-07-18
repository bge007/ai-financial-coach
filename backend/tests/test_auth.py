from authlib.jose import jwt

from app.core.auth import COOKIE_NAME, create_session_token, decode_session_token


def test_me_requires_auth(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_rejects_garbage_token(client):
    client.cookies.set(COOKIE_NAME, "not-a-jwt")
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_wrong_signature(client):
    forged = jwt.encode(
        {"alg": "HS256"}, {"sub": "1", "exp": 9999999999}, "wrong-secret"
    )
    if isinstance(forged, bytes):
        forged = forged.decode()
    client.cookies.set(COOKIE_NAME, forged)
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_expired_token(client):
    expired = jwt.encode(
        {"alg": "HS256"}, {"sub": "1", "iat": 1, "exp": 2}, "test-secret-key"
    )
    if isinstance(expired, bytes):
        expired = expired.decode()
    client.cookies.set(COOKIE_NAME, expired)
    assert client.get("/auth/me").status_code == 401


def test_token_roundtrip():
    token = create_session_token(42)
    assert decode_session_token(token) == 42


def test_decode_rejects_tampering():
    token = create_session_token(42)
    assert decode_session_token(token[:-2] + "xx") is None


def test_callback_creates_user_and_me_returns_it(client, monkeypatch):
    from app.api import auth as auth_api

    async def fake_authorize_access_token(request):
        return {
            "userinfo": {"sub": "google-sub-123", "email": "asha@example.com", "name": "Asha"}
        }

    monkeypatch.setattr(
        auth_api.oauth.google, "authorize_access_token", fake_authorize_access_token
    )

    r = client.get("/auth/callback", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert COOKIE_NAME in r.headers.get("set-cookie", "")

    me = client.get("/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "asha@example.com"
    assert body["name"] == "Asha"
    assert isinstance(body["id"], int)

    # same google_sub logging in again must not create a second user
    r2 = client.get("/auth/callback", follow_redirects=False)
    assert r2.status_code in (302, 307)
    me2 = client.get("/auth/me")
    assert me2.json()["id"] == body["id"]


def test_logout_clears_session(client, monkeypatch):
    from app.api import auth as auth_api

    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": "g-456", "email": "b@example.com", "name": "B"}}

    monkeypatch.setattr(
        auth_api.oauth.google, "authorize_access_token", fake_authorize_access_token
    )
    client.get("/auth/callback", follow_redirects=False)
    assert client.get("/auth/me").status_code == 200

    client.post("/auth/logout", follow_redirects=False)
    assert client.get("/auth/me").status_code == 401
