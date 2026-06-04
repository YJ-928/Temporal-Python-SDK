"""
Database configuration.

SQLAlchemy async setup for database persistence.
Configure DATABASE_URL in .env to enable database functionality.
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from .settings import settings
from .logger import get_logger


logger = get_logger(__name__)

Base = declarative_base()

engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker] = None


def init_engine() -> None:
    """
    Initialize database engine and session factory.

    Called automatically when DATABASE_URL is configured.
    """
    global engine, async_session_factory

    if not settings.DATABASE_URL:
        logger.info("DATABASE_URL not configured - database features disabled")
        return

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("Database engine initialized")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints to get database sessions.

    Usage in endpoint:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession instance

    Raises:
        RuntimeError: If database is not configured
    """
    if not async_session_factory:
        logger.error("Database session requested but DATABASE_URL not configured")
        raise RuntimeError("Database not configured. Set DATABASE_URL in .env file")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in Base.metadata.
    Call this on application startup after defining models.
    """
    if not engine:
        logger.warning("Database engine not initialized - skipping table creation")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")


async def close_db() -> None:
    """
    Close database connections.

    Call this on application shutdown.
    """
    if engine:
        await engine.dispose()
        logger.info("Database connections closed")


init_engine()
