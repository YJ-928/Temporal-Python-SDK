"""
WorkflowRegistration repository — replaces registrations.json.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.model.workflow_registration import WorkflowRegistration
from .base_repo import BaseRepo


class WorkflowRegistrationRepo(BaseRepo[WorkflowRegistration]):
    def __init__(self) -> None:
        super().__init__(WorkflowRegistration)

    async def get_by_hash(self, content_hash: str, db: AsyncSession) -> WorkflowRegistration | None:
        result = await db.execute(
            select(WorkflowRegistration).where(WorkflowRegistration.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def get_all_registered(self, db: AsyncSession) -> list[WorkflowRegistration]:
        result = await db.execute(
            select(WorkflowRegistration).where(WorkflowRegistration.registered.is_(True))
        )
        return list(result.scalars().all())

    async def set_runtime_loaded(self, content_hash: str, db: AsyncSession) -> None:
        reg = await self.get_by_hash(content_hash, db)
        if reg:
            reg.runtime_loaded = True
            await db.flush()

    async def mark_all_runtime_loaded(self, db: AsyncSession) -> None:
        regs = await self.get_all_registered(db)
        for r in regs:
            r.runtime_loaded = True
        await db.flush()
