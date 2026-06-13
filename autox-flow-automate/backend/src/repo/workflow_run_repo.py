"""
WorkflowRun repository — execution history cache.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.model.workflow_run import WorkflowRun
from .base_repo import BaseRepo


class WorkflowRunRepo(BaseRepo[WorkflowRun]):
    def __init__(self) -> None:
        super().__init__(WorkflowRun)

    async def get_by_run_id(self, run_id: str, db: AsyncSession) -> WorkflowRun | None:
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.run_id == run_id)
        )
        return result.scalar_one_or_none()

    async def get_runs_for_workflow(
        self, workflow_db_id: int, db: AsyncSession
    ) -> list[WorkflowRun]:
        result = await db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_db_id)
            .order_by(WorkflowRun.id.desc())
        )
        return list(result.scalars().all())
