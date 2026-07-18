from app.core.config import Settings, get_settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./elsewhere.db")
    monkeypatch.setenv("SECRET_KEY", "s3cret")
    monkeypatch.setenv("LLM_MODEL", "anthropic/claude-sonnet-4.5")
    s = Settings(_env_file=None)
    assert s.database_url == "sqlite+aiosqlite:///./elsewhere.db"
    assert s.secret_key == "s3cret"
    assert s.llm_model == "anthropic/claude-sonnet-4.5"


def test_settings_have_sane_defaults():
    s = Settings(_env_file=None)
    assert s.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert s.qdrant_url.startswith("http")
    assert s.oauth_redirect_uri.endswith("/auth/callback")


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
