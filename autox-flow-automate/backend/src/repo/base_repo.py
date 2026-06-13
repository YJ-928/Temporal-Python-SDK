"""
Generic typed CRUD base repository.
"""
from typing import Generic, TypeVar, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.model.base import Base

T = TypeVar("T", bound=Base)


class BaseRepo(Generic[T]):
    def __init__(self, model: Type[T]) -> None:
        self.model = model

    async def _get_session(self) -> AsyncSession:
        from src.config.db_config import get_session_factory
        return get_session_factory()()

    async def get(self, id: int, db: AsyncSession | None = None) -> T | None:
        session = db or await self._get_session()
        own = db is None
        try:
            result = await session.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
            return result.scalar_one_or_none()
        finally:
            if own:
                await session.close()

    async def get_all(self, db: AsyncSession | None = None) -> list[T]:
        session = db or await self._get_session()
        own = db is None
        try:
            result = await session.execute(select(self.model))
            return list(result.scalars().all())
        finally:
            if own:
                await session.close()

    async def save(self, obj: T, db: AsyncSession) -> T:
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def delete(self, id: int, db: AsyncSession) -> bool:
        obj = await self.get(id, db)
        if obj is None:
            return False
        await db.delete(obj)
        await db.flush()
        return True
