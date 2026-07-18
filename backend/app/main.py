from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.auth import router as auth_router
from app.core.config import get_settings
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="AI Financial Coach", version="0.1.0", lifespan=lifespan)

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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
