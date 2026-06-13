"""
WorkflowRun — execution history cache from Temporal.
"""
from sqlalchemy import String, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from .enums import WorkflowRunStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .workflow import Workflow


class WorkflowRun(Base, TimestampMixin):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False, index=True)
    temporal_workflow_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_type: Mapped[str] = mapped_column(String(255), nullable=False)
    task_queue: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=WorkflowRunStatus.RUNNING.value
    )
    input_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="runs")
