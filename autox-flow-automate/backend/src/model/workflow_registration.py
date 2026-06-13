"""
WorkflowRegistration — tracks whether a compiled version is registered in the Zigflow runtime.
Replaces the file-based registrations.json.
"""
from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .workflow import Workflow


class WorkflowRegistration(Base, TimestampMixin):
    __tablename__ = "workflow_registrations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    workflow_type: Mapped[str] = mapped_column(String(255), nullable=False)
    task_queue: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    runtime_loaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="registrations")
