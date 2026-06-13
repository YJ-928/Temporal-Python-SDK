"""
FastAPI dependency: yields an AsyncSession per request.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.db_config import get_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        async with session.begin():
            yield session
