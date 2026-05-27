#!/usr/bin/env python3
"""Start the Temporal worker for the Parent Orchestrator Workflow.

Usage (from Docker/long_running_workflow/orchestrator/):
    python ../scripts/start_worker.py
    python ../scripts/start_worker.py --temporal-host localhost:7233
"""
from __future__ import annotations

import asyncio
import argparse
import os
import sys

# Allow running from the scripts/ directory
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCHESTRATOR_DIR = os.path.join(_SCRIPTS_DIR, "..", "orchestrator")
sys.path.insert(0, _ORCHESTRATOR_DIR)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Start Temporal worker for ParentOrchestratorWorkflow")
    p.add_argument("--temporal-host", default=os.getenv("TEMPORAL_HOST", "localhost:7233"))
    p.add_argument("--namespace", default=os.getenv("TEMPORAL_NAMESPACE", "default"))
    p.add_argument("--task-queue", default=os.getenv("TASK_QUEUE", "orchestrator-queue"))
    return p.parse_args()


async def main() -> None:
    args = parse_args()
    os.environ.setdefault("TEMPORAL_HOST", args.temporal_host)
    os.environ.setdefault("TEMPORAL_NAMESPACE", args.namespace)
    os.environ.setdefault("TASK_QUEUE", args.task_queue)

    # Import after env vars are set so Settings picks them up
    from app.temporal.worker import main as worker_main
    await worker_main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWorker stopped.")
