import os

import pytest
from fastapi.testclient import TestClient

from app.core.auth import DEMO_EMAIL


@pytest.fixture
def disabled_auth_client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import app

    with TestClient(app) as c:
        yield c

    monkeypatch.setenv("AUTH_DISABLED", "false")
    get_settings.cache_clear()


def test_me_succeeds_without_any_cookie(disabled_auth_client):
    r = disabled_auth_client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == DEMO_EMAIL


def test_demo_user_is_stable_across_requests(disabled_auth_client):
    first = disabled_auth_client.get("/auth/me").json()["id"]
    second = disabled_auth_client.get("/auth/me").json()["id"]
    assert first == second


def test_garbage_cookie_is_ignored_when_disabled(disabled_auth_client):
    disabled_auth_client.cookies.set("session", "not-a-jwt")
    r = disabled_auth_client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == DEMO_EMAIL
