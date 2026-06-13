"""
SQLAlchemy async engine + session factory for PostgreSQL.
"""
from functools import lru_cache
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool


def _build_dsn(s) -> str:
    return (
        f"postgresql+asyncpg://{s.DATABASE_USERNAME}:{s.DATABASE_PASSWORD}"
        f"@{s.DATABASE_HOST}:{s.DATABASE_PORT}/{s.DATABASE_NAME}"
    )


@lru_cache
def get_engine() -> AsyncEngine:
    from .settings import settings
    # Set DB_ECHO=True in .env to log all SQL queries to stdout (useful for debugging)
    return create_async_engine(
        _build_dsn(settings),
        poolclass=AsyncAdaptedQueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        echo=settings.DB_ECHO,
        future=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def init_models() -> None:
    """Create all tables — dev only. Use Alembic migrations in production."""
    from src.model.base import Base
    import src.model  # noqa: F401 — side-effect: registers all models with Base.metadata
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
