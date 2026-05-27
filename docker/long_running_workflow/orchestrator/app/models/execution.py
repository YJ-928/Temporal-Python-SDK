"""In-memory execution record model and thread-safe store."""
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ExecutionRecord:
    execution_id: str
    workflow: str
    workflow_path: str
    input: Dict[str, Any]
    status: ExecutionStatus = ExecutionStatus.PENDING
    container_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class ExecutionStore:
    """Thread-safe in-memory store for execution records.

    In production, replace with a persistent backend (Redis, PostgreSQL, etc.)
    so that records survive service restarts. Temporal provides durability at
    the orchestration layer — this store is only for the API query surface.
    """

    def __init__(self) -> None:
        self._records: Dict[str, ExecutionRecord] = {}
        self._lock = Lock()

    def create(
        self,
        workflow: str,
        workflow_path: str,
        input_data: Dict[str, Any],
    ) -> ExecutionRecord:
        execution_id = str(uuid.uuid4())
        record = ExecutionRecord(
            execution_id=execution_id,
            workflow=workflow,
            workflow_path=workflow_path,
            input=input_data,
        )
        with self._lock:
            self._records[execution_id] = record
        return record

    def get(self, execution_id: str) -> Optional[ExecutionRecord]:
        with self._lock:
            return self._records.get(execution_id)

    def update(self, execution_id: str, **kwargs: Any) -> Optional[ExecutionRecord]:
        with self._lock:
            record = self._records.get(execution_id)
            if record is None:
                return None
            for key, value in kwargs.items():
                setattr(record, key, value)
            record.updated_at = time.time()
            return record

    def list_all(self) -> List[ExecutionRecord]:
        with self._lock:
            return list(self._records.values())
