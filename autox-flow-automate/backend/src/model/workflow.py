"""
Workflow — top-level identity record (one per workflow_id).
"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .workflow_version import WorkflowVersion
    from .workflow_registration import WorkflowRegistration
    from .workflow_run import WorkflowRun


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    versions: Mapped[list["WorkflowVersion"]] = relationship(
        "WorkflowVersion", back_populates="workflow", cascade="all, delete-orphan"
    )
    registrations: Mapped[list["WorkflowRegistration"]] = relationship(
        "WorkflowRegistration", back_populates="workflow", cascade="all, delete-orphan"
    )
    runs: Mapped[list["WorkflowRun"]] = relationship(
        "WorkflowRun", back_populates="workflow", cascade="all, delete-orphan"
    )
