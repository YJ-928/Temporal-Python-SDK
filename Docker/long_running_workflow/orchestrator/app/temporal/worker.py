"""Temporal worker entry point for the Parent Orchestrator Workflow.

Run this process persistently alongside the FastAPI service.
It polls the ``orchestrator-queue`` task queue and executes both the
workflow code (``ParentOrchestratorWorkflow``) and the activity code
(``execute_workflow_activity``).
"""
from __future__ import annotations

import asyncio
import logging
import sys

from temporalio.client import Client
from temporalio.worker import Worker

from app.temporal.activities import execute_workflow_activity
from app.temporal.workflows import ParentOrchestratorWorkflow
from app.utils.config import get_settings
from app.utils.logging import setup_logging

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

TASK_QUEUE = settings.TASK_QUEUE


async def main() -> None:
    logger.info(
        "Connecting to Temporal",
        extra={"host": settings.TEMPORAL_HOST, "namespace": settings.TEMPORAL_NAMESPACE},
    )
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )

    logger.info(
        "Starting Temporal worker",
        extra={"task_queue": TASK_QUEUE},
    )
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ParentOrchestratorWorkflow],
        activities=[execute_workflow_activity],
    )

    logger.info("Worker running — polling for tasks (Ctrl+C to stop)")
    try:
        await worker.run()
    except asyncio.CancelledError:
        logger.info("Worker shutdown requested")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
        sys.exit(0)
