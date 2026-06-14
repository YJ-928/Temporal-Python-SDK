"""Parent Orchestrator Workflow — durable, infinite-running Temporal workflow.

Design
------
- Accepts ``execute_workflow`` signals carrying a workflow name + input dict.
- Dispatches each execution via the ``execute_workflow_activity`` which calls
  the External Execution Orchestrator API (FastAPI).
- The API creates an ephemeral Docker container, runs the Zigflow workflow,
  collects the result, destroys the container, and returns.
- Uses ``continue_as_new`` after ``MAX_EXECUTIONS_BEFORE_CAN`` iterations to
  prevent Temporal's event history from growing unboundedly.
- State carried across ``continue_as_new`` boundaries: execution count + the
  last 10 result summaries (for the query surface).

Signal contract
---------------
Signal name : ``execute_workflow``
Payload     : single JSON object
  {
    "workflow": "hello-world.json",
    "input":    {"name": "Yash"}
  }
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from app.temporal.activities import execute_workflow_activity

# Constants
MAX_EXECUTIONS_BEFORE_CAN = 50  # call continue_as_new every N executions


# Data models

@dataclass
class ExecutionResultSummary:
    execution_id: str
    workflow: str
    status: str
    container_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class OrchestratorState:
    """State carried across continue_as_new boundaries."""
    execution_count: int = 0
    results: List[ExecutionResultSummary] = field(default_factory=list)


# Workflow definition

@workflow.defn
class ParentOrchestratorWorkflow:
    """Long-running durable orchestrator.

    Listens for ``execute_workflow`` signals indefinitely. Each signal triggers
    an isolated Docker container execution via the External Execution API.
    """

    def __init__(self) -> None:
        self._pending: List[Dict[str, Any]] = []
        self._results: List[ExecutionResultSummary] = []
        self._execution_count: int = 0
        self._stop: bool = False

    # Signals

    @workflow.signal
    def execute_workflow(self, payload: Dict[str, Any]) -> None:
        """Receive a workflow execution request.

        Expected payload::

            {"workflow": "hello-world.json", "input": {"name": "Yash"}}
        """
        self._pending.append(payload)
        workflow.logger.info(
            "Signal received: execute_workflow",
            extra={"workflow": payload.get("workflow"), "queue_depth": len(self._pending)},
        )

    @workflow.signal
    def stop(self) -> None:
        """Gracefully stop the orchestrator after all pending executions drain."""
        self._stop = True
        workflow.logger.info("Stop signal received — draining pending executions")

    # Queries

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        return {
            "executionCount": self._execution_count,
            "pendingCount": len(self._pending),
            "completedResults": len(self._results),
            "stopping": self._stop,
        }

    @workflow.query
    def get_results(self) -> List[ExecutionResultSummary]:
        return self._results

    @workflow.query
    def get_last_result(self) -> Optional[ExecutionResultSummary]:
        return self._results[-1] if self._results else None

    # Entry point

    @workflow.run
    async def run(self, state: Optional[OrchestratorState] = None) -> None:
        """Infinite orchestration loop.

        Accepts an optional ``OrchestratorState`` from a previous
        ``continue_as_new`` invocation so execution count and recent results
        survive the history reset.
        """
        if state:
            self._execution_count = state.execution_count
            self._results = state.results[-10:]  # carry last 10 summaries

        workflow.logger.info(
            "ParentOrchestratorWorkflow started",
            extra={"execution_count": self._execution_count},
        )

        while True:
            # Block until at least one signal arrives or a stop is requested
            await workflow.wait_condition(
                lambda: bool(self._pending) or self._stop
            )

            if self._stop and not self._pending:
                workflow.logger.info("Orchestrator stopped gracefully")
                break

            # Drain all pending signals before waiting again
            while self._pending:
                payload = self._pending.pop(0)
                await self._dispatch(payload)

                # Prevent unbounded history growth
                if self._execution_count >= MAX_EXECUTIONS_BEFORE_CAN:
                    carry = OrchestratorState(
                        execution_count=self._execution_count,
                        results=self._results[-10:],
                    )
                    workflow.logger.info(
                        "Calling continue_as_new",
                        extra={"execution_count": self._execution_count},
                    )
                    workflow.continue_as_new(carry)
                    return  # unreachable; satisfies type checker

    # Internal helpers

    async def _dispatch(self, payload: Dict[str, Any]) -> None:
        """Dispatch one execution to the External Execution Orchestrator API."""
        workflow_name: str = payload.get("workflow", "")
        input_data: Dict[str, Any] = payload.get("input", {})

        if not workflow_name:
            workflow.logger.error("Signal payload missing 'workflow' field — skipping")
            self._execution_count += 1
            return

        workflow.logger.info(
            "Dispatching execution",
            extra={"workflow": workflow_name, "execution_count": self._execution_count + 1},
        )

        try:
            api_result: Dict[str, Any] = await workflow.execute_activity(
                execute_workflow_activity,
                args=[workflow_name, input_data],
                start_to_close_timeout=timedelta(hours=1),
                heartbeat_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(minutes=2),
                    maximum_attempts=3,
                    non_retryable_error_types=["FileNotFoundError"],
                ),
            )
            summary = ExecutionResultSummary(
                execution_id=api_result.get("executionId", "unknown"),
                workflow=workflow_name,
                status=api_result.get("status", "unknown"),
                container_id=api_result.get("containerId"),
                result=api_result.get("result"),
                error=api_result.get("error"),
            )

        except ApplicationError as exc:
            workflow.logger.error(
                "Execution failed (non-retryable)",
                extra={"workflow": workflow_name, "error": str(exc)},
            )
            summary = ExecutionResultSummary(
                execution_id="error",
                workflow=workflow_name,
                status="failed",
                error=str(exc),
            )
        except Exception as exc:
            workflow.logger.error(
                "Execution failed",
                extra={"workflow": workflow_name, "error": str(exc)},
            )
            summary = ExecutionResultSummary(
                execution_id="error",
                workflow=workflow_name,
                status="failed",
                error=str(exc),
            )

        self._results.append(summary)
        self._execution_count += 1
        workflow.logger.info(
            "Execution recorded",
            extra={
                "workflow": workflow_name,
                "status": summary.status,
                "execution_count": self._execution_count,
            },
        )
