import asyncio
import os
from pathlib import Path

# Must be set before any app import: the async engine is built at import time.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "test"
os.environ["QDRANT_URL"] = ":memory:"
# Real auth enforcement is the default under test; test_auth_disabled.py
# flips this on explicitly to exercise the bypass path.
os.environ["AUTH_DISABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import Base, engine
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


async def _clear_db() -> None:
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(text(f"DELETE FROM {table.name}"))


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def client():
    # context manager runs the lifespan -> creates tables in the in-memory DB
    with TestClient(app) as c:
        yield c
    # Reset shared in-memory DB so tests stay independent.
    asyncio.run(_clear_db())


@pytest.fixture
def auth_client(client, monkeypatch):
    """TestClient authenticated as a fixed user via mocked Google callback."""
    from app.api import auth as auth_api

    async def fake_authorize_access_token(request):
        return {
            "userinfo": {
                "sub": "google-user-a",
                "email": "asha@example.com",
                "name": "Asha",
            }
        }

    monkeypatch.setattr(
        auth_api.oauth.google, "authorize_access_token", fake_authorize_access_token
    )
    client.get("/auth/callback", follow_redirects=False)
    return client


def login_as(client, monkeypatch, *, sub: str, email: str, name: str):
    """Authenticate the client as a specific Google identity."""
    from app.api import auth as auth_api

    async def fake_authorize_access_token(request):
        return {"userinfo": {"sub": sub, "email": email, "name": name}}

    monkeypatch.setattr(
        auth_api.oauth.google, "authorize_access_token", fake_authorize_access_token
    )
    # Clear any prior session cookie so the new login sticks.
    client.cookies.clear()
    client.get("/auth/callback", follow_redirects=False)
    return client
