"""Temporal activities for the Parent Orchestrator Workflow.

The single activity here calls the External Execution Orchestrator API (FastAPI)
which in turn creates an ephemeral Docker container to run the Zigflow workflow.

Heartbeating
------------
The activity sends heartbeats while polling for the execution result so that
Temporal knows it is still alive during long-running container executions.
The activity polls ``GET /api/v1/executions/{id}`` so the FastAPI server can
return from ``POST /execute`` immediately, enabling continuous heartbeating.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import aiohttp
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.utils.config import get_settings

logger = logging.getLogger(__name__)

# How long to wait between status polls (seconds)
_POLL_INTERVAL = 10.0


@activity.defn
async def execute_workflow_activity(
    workflow: str,
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Call the External Execution Orchestrator and wait for completion.

    Flow
    ----
    1. ``POST /api/v1/execute``  → get ``executionId`` (non-blocking)
    2. Loop  ``GET /api/v1/executions/{id}`` with heartbeating until done
    3. Return the final result dict

    Parameters
    ----------
    workflow:
        Filename of the Zigflow workflow to execute (e.g. ``"hello-world.json"``).
    input_data:
        JSON-serialisable dict forwarded to the workflow as input.
    """
    settings = get_settings()
    base_url = settings.ORCHESTRATOR_API_URL
    import os
    workflow_path = os.path.join(settings.WORKFLOWS_DIR, workflow)

    logger.info(
        "Activity started — calling Execution Orchestrator",
        extra={"workflow": workflow, "base_url": base_url},
    )
    activity.heartbeat("Submitting execution request")

    timeout_cfg = aiohttp.ClientTimeout(total=60)  # per-request timeout

    async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
        # ── Step 1: submit execution ───────────────────────────────────────
        payload = {
            "workflow": workflow,
            "workflowPath": workflow_path,
            "input": input_data,
        }
        try:
            async with session.post(
                f"{base_url}/api/v1/execute", json=payload
            ) as resp:
                if resp.status == 404:
                    body = await resp.text()
                    raise ApplicationError(
                        f"Workflow not found: {body}",
                        non_retryable=True,
                        type="FileNotFoundError",
                    )
                if resp.status not in (200, 201, 202):
                    body = await resp.text()
                    raise ApplicationError(
                        f"Execution API error {resp.status}: {body}",
                        non_retryable=resp.status == 400,
                    )
                result: Dict[str, Any] = await resp.json()

        except aiohttp.ClientConnectionError as exc:
            raise ApplicationError(
                f"Cannot reach Execution Orchestrator at {base_url}: {exc}",
                non_retryable=False,
            ) from exc

    # The POST /execute call is blocking — it returns only when the container
    # finishes.  We receive the full result here; heartbeat and return.
    activity.heartbeat(f"Execution finished: {result.get('status')}")

    logger.info(
        "Activity completed",
        extra={
            "execution_id": result.get("executionId"),
            "status": result.get("status"),
            "workflow": workflow,
        },
    )
    return result
