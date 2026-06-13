"""
WorkflowVersion — one record per compiled DSL version (keyed by content hash).
"""
from sqlalchemy import String, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .workflow import Workflow


class WorkflowVersion(Base, TimestampMixin):
    __tablename__ = "workflow_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    content_hash: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    dsl_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    rf_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    workflow_type: Mapped[str] = mapped_column(String(255), nullable=False)
    task_queue: Mapped[str] = mapped_column(String(255), nullable=False)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="versions")
