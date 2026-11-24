from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


def _ensure_sqlite_directory(database_url: str) -> None:
    """Create the parent directory for file-backed SQLite databases if needed."""
    url = make_url(database_url)
    if url.drivername.startswith("sqlite") and url.database and url.database != ":memory:":
        Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def create_engine_for_url(database_url: str, *, echo: bool = False) -> AsyncEngine:
    """Create an async SQLAlchemy engine configured for SQLite foreign-key safety."""
    _ensure_sqlite_directory(database_url)
    async_engine = create_async_engine(database_url, echo=echo, future=True)

    if make_url(database_url).drivername.startswith("sqlite"):

        @event.listens_for(async_engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return async_engine


settings = get_settings()
engine = create_engine_for_url(
    settings.database_url,
    echo=settings.app_env == "development",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db(
    *,
    target_engine: AsyncEngine | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    seed: bool = True,
) -> None:
    """Create database tables and optionally populate initial seed data."""
    # Ensure ORM models are registered on Base.metadata before create_all.
    import app.models.domain  # noqa: F401
    from app.db.seed import seed_database

    db_engine = target_engine or engine
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if seed:
        factory = session_factory or AsyncSessionLocal
        async with factory() as session:
            await seed_database(session)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI request dependencies."""
    async with AsyncSessionLocal() as session:
        yield session
