"""
Workflow repository — get or create Workflow records.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.model.workflow import Workflow
from .base_repo import BaseRepo


class WorkflowRepo(BaseRepo[Workflow]):
    def __init__(self) -> None:
        super().__init__(Workflow)

    async def get_by_workflow_id(self, workflow_id: str, db: AsyncSession) -> Workflow | None:
        result = await db.execute(
            select(Workflow).where(Workflow.workflow_id == workflow_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, workflow_id: str, name: str, db: AsyncSession) -> Workflow:
        existing = await self.get_by_workflow_id(workflow_id, db)
        if existing:
            return existing
        obj = Workflow(workflow_id=workflow_id, name=name, description="")
        return await self.save(obj, db)
