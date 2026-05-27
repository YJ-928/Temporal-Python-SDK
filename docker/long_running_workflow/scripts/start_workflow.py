#!/usr/bin/env python3
"""Start the Parent Orchestrator Workflow in Temporal.

Usage:
    python scripts/start_workflow.py
    python scripts/start_workflow.py --workflow-id my-orchestrator --temporal-host localhost:7233

The workflow runs indefinitely until a 'stop' signal is sent.
Watch progress in the Temporal Web UI: http://localhost:8233
"""
from __future__ import annotations

import asyncio
import argparse
import os
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCHESTRATOR_DIR = os.path.join(_SCRIPTS_DIR, "..", "orchestrator")
sys.path.insert(0, _ORCHESTRATOR_DIR)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Start the Parent Orchestrator Workflow")
    p.add_argument(
        "--workflow-id",
        default="parent-orchestrator-01",
        help="Temporal workflow ID (must be unique per active run)",
    )
    p.add_argument("--temporal-host", default=os.getenv("TEMPORAL_HOST", "localhost:7233"))
    p.add_argument("--namespace", default=os.getenv("TEMPORAL_NAMESPACE", "default"))
    p.add_argument("--task-queue", default=os.getenv("TASK_QUEUE", "orchestrator-queue"))
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    from temporalio.client import Client
    from app.temporal.workflows import ParentOrchestratorWorkflow

    print(f"Connecting to Temporal at {args.temporal_host} ...")
    client = await Client.connect(args.temporal_host, namespace=args.namespace)

    handle = await client.start_workflow(
        ParentOrchestratorWorkflow.run,
        id=args.workflow_id,
        task_queue=args.task_queue,
    )

    print(f"\nParent Orchestrator Workflow started successfully!")
    print(f"  Workflow ID : {handle.id}")
    print(f"  Run ID      : {handle.result_run_id}")
    print(f"  Task queue  : {args.task_queue}")
    print(f"\nMonitor at  : http://localhost:8233/namespaces/{args.namespace}/workflows/{handle.id}")
    print(f"\nSend a signal:")
    print(f'  python scripts/send_signal.py --workflow-id {handle.id} \\')
    print(f'      --workflow hello-world.json --input \'{{"name":"Yash"}}\'')
    print(f"\nQuery status:")
    print(f"  temporal workflow query --workflow-id {handle.id} --type get_status")
    print(f"\nStop the orchestrator:")
    print(f"  temporal workflow signal --workflow-id {handle.id} --name stop")


if __name__ == "__main__":
    asyncio.run(main())
