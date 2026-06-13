"""
WorkflowVersion repository.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.model.workflow_version import WorkflowVersion
from .base_repo import BaseRepo


class WorkflowVersionRepo(BaseRepo[WorkflowVersion]):
    def __init__(self) -> None:
        super().__init__(WorkflowVersion)

    async def get_by_hash(self, content_hash: str, db: AsyncSession) -> WorkflowVersion | None:
        result = await db.execute(
            select(WorkflowVersion).where(WorkflowVersion.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def get_latest_for_workflow(
        self, workflow_db_id: int, db: AsyncSession
    ) -> WorkflowVersion | None:
        result = await db.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_db_id)
            .order_by(WorkflowVersion.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
