from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.ask import router as ask_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.privacy import router as privacy_router
from app.api.profile import router as profile_router
from app.api.transactions import router as transactions_router
from app.api.upload import router as upload_router
from app.core.config import get_settings
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="MoneyMitra", version="0.1.0", lifespan=lifespan)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# authlib needs a session to hold the OAuth state between /login and /callback
app.add_middleware(
    SessionMiddleware, secret_key=settings.secret_key, same_site="lax"
)

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(profile_router)
app.include_router(transactions_router)
app.include_router(ask_router)
app.include_router(dashboard_router)
app.include_router(privacy_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
async def metrics() -> dict:
    """Lightweight hackathon metrics endpoint (no Prometheus scrape required)."""
    return {
        "status": "ok",
        "service": "moneymitra",
        "note": "Agent token/latency details are logged per /api/ask run",
    }
