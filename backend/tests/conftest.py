import os

# Must be set before any app import: the async engine is built at import time.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "test"
# Real auth enforcement is the default under test; test_auth_disabled.py
# flips this on explicitly to exercise the bypass path.
os.environ["AUTH_DISABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # context manager runs the lifespan -> creates tables in the in-memory DB
    with TestClient(app) as c:
        yield c
