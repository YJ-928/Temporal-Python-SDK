"""
DB-level enums for ORM columns.
"""
from enum import Enum


class WorkflowRunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TERMINATED = "TERMINATED"
    TIMED_OUT = "TIMED_OUT"
    UNKNOWN = "UNKNOWN"
