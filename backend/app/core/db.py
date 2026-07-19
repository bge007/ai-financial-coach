from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    settings = get_settings()
    url = settings.database_url
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite+aiosqlite://", "sqlite+aiosqlite:///:memory:"):
            # in-memory DB (tests): share one connection across sessions
            kwargs["poolclass"] = StaticPool
        else:
            # ensure the directory holding the .db file exists
            db_path = url.split("///", 1)[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(url, **kwargs)


engine = _build_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _sync_database_url() -> str:
    return get_settings().database_url.replace("+aiosqlite", "")


def _infer_legacy_revision(insp) -> str | None:
    """Map an existing create_all schema to the latest applied alembic revision."""
    if not insp.has_table("users"):
        return None
    if insp.has_table("user_profiles"):
        return "0004"
    if insp.has_table("category_rules"):
        return "0003"
    if insp.has_table("transactions"):
        return "0002"
    return "0001"


def _run_alembic_migrations() -> None:
    """Apply pending alembic revisions (handles legacy DBs created via create_all)."""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text

    backend_dir = Path(__file__).resolve().parents[2]
    cfg = Config(str(backend_dir / "alembic.ini"))
    sync_url = _sync_database_url()
    sync_engine = create_engine(sync_url)
    insp = inspect(sync_engine)

    with sync_engine.connect() as conn:
        if insp.has_table("alembic_version"):
            row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            if row and row[0]:
                command.upgrade(cfg, "head")
                return

        legacy = _infer_legacy_revision(insp)
        if legacy:
            command.stamp(cfg, legacy)

    command.upgrade(cfg, "head")


async def init_db() -> None:
    """Ensure schema exists and apply alembic migrations."""
    import asyncio

    from app import models  # noqa: F401  (register models on Base.metadata)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await asyncio.to_thread(_run_alembic_migrations)
