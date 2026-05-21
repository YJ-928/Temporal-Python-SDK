#!/usr/bin/env python3
"""Send an 'execute_workflow' signal to the Parent Orchestrator Workflow.

Usage:
    python scripts/send_signal.py --workflow hello-world.json --input '{"name":"Yash"}'
    python scripts/send_signal.py --workflow parallel.json --input '{}'
    python scripts/send_signal.py --workflow-id my-orchestrator --workflow signal.json

After sending, the orchestrator creates an ephemeral Docker container,
runs the specified Zigflow workflow, and returns the result.
"""
from __future__ import annotations

import asyncio
import argparse
import json
import os
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCHESTRATOR_DIR = os.path.join(_SCRIPTS_DIR, "..", "orchestrator")
sys.path.insert(0, _ORCHESTRATOR_DIR)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Send an execute_workflow signal to the Parent Orchestrator"
    )
    p.add_argument(
        "--workflow-id",
        default="parent-orchestrator-01",
        help="Target Parent Orchestrator workflow ID",
    )
    p.add_argument(
        "--workflow",
        required=True,
        help="Zigflow workflow filename to execute (e.g. hello-world.json)",
    )
    p.add_argument(
        "--input",
        default="{}",
        help='JSON-encoded workflow input (default: {})',
    )
    p.add_argument("--temporal-host", default=os.getenv("TEMPORAL_HOST", "localhost:7233"))
    p.add_argument("--namespace", default=os.getenv("TEMPORAL_NAMESPACE", "default"))
    p.add_argument(
        "--wait",
        action="store_true",
        default=False,
        help="Query and print status after sending the signal",
    )
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    try:
        input_data: dict = json.loads(args.input)
    except json.JSONDecodeError as exc:
        print(f"ERROR: --input is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    from temporalio.client import Client
    from app.temporal.workflows import ParentOrchestratorWorkflow

    print(f"Connecting to Temporal at {args.temporal_host} ...")
    client = await Client.connect(args.temporal_host, namespace=args.namespace)
    handle = client.get_workflow_handle(args.workflow_id)

    # Signal payload matches the workflow's execute_workflow signal signature:
    # def execute_workflow(self, payload: Dict[str, Any]) -> None
    signal_payload = {
        "workflow": args.workflow,
        "input": input_data,
    }

    print(f"\nSending signal 'execute_workflow' to workflow '{args.workflow_id}'")
    print(f"  Workflow : {args.workflow}")
    print(f"  Input    : {json.dumps(input_data)}")

    await handle.signal(ParentOrchestratorWorkflow.execute_workflow, signal_payload)
    print("\nSignal sent successfully!")

    if args.wait:
        import asyncio as _asyncio
        print("\nWaiting 2 seconds then querying status...")
        await _asyncio.sleep(2)
        status = await handle.query(ParentOrchestratorWorkflow.get_status)
        print(f"\nOrchestrator status:\n{json.dumps(status, indent=2)}")

        last = await handle.query(ParentOrchestratorWorkflow.get_last_result)
        if last:
            print(f"\nLast execution result:\n{json.dumps(last.__dict__, indent=2, default=str)}")

    print(f"\nMonitor at: http://localhost:8233/namespaces/{args.namespace}/workflows/{args.workflow_id}")


if __name__ == "__main__":
    asyncio.run(main())
