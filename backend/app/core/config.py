from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...]:
    """Prefer repo-root .env (hackathon layout), then cwd .env."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / ".env",  # .../ai-financial-coach/.env
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]
    found = [str(p) for p in candidates if p.is_file()]
    return tuple(found) or (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(), env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/coach.db"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "user_docs"
    embedding_dim: int = 384
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:8000/auth/callback"

    # LLM provider — OpenRouter (OpenAI-compatible)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "anthropic/claude-sonnet-4.5"

    # App
    secret_key: str = "change-me"
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Dev-only bypass: skip Google OAuth and auto-authenticate a fixed demo
    # user. The OAuth flow and get_current_user enforcement stay fully intact
    # and are exercised by tests with this flag off. NEVER set true in prod.
    auth_disabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
