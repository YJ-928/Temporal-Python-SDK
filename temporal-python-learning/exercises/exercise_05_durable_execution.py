"""
Exercise 05 — Durable Execution

Objective:
    Create a Workflow with two Activities and a durable timer.
    Demonstrate that the Workflow survives a Worker crash.

Concepts:
    - Durable timers (asyncio.sleep)
    - Event history replay
    - Activity result caching during replay
    - workflow.logger for replay-safe logging

Instructions:
    1. Start Temporal dev server: temporal server start-dev
    2. Run the Worker:   python exercise_05_durable_execution.py worker
    3. Run the Starter:  python exercise_05_durable_execution.py starter

    To demonstrate durability:
    4. Run the Starter again
    5. Kill the Worker (Ctrl+C) while "Sleeping for 10 seconds..." is shown
    6. Restart the Worker
    7. Observe that the Workflow completes without re-executing Activity 1

Expected output:
    Step 1 result: Step 1 completed at <timestamp>
    Sleeping for 10 seconds...
    Step 2 result: Step 2 completed at <timestamp>
    Final result: Step 1 completed at ... | Step 2 completed at ...
"""

import asyncio
import sys
from datetime import timedelta
from time import time

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


# --- Activities ---

@activity.defn
async def step_one() -> str:
    """First step — simulates an API call."""
    activity.logger.info("Executing step one...")
    return f"Step 1 completed at {int(time())}"


@activity.defn
async def step_two() -> str:
    """Second step — simulates a database write."""
    activity.logger.info("Executing step two...")
    return f"Step 2 completed at {int(time())}"


# --- Workflow ---

@workflow.defn
class DurableExecutionWorkflow:
    """Workflow demonstrating durable execution with a timer."""

    @workflow.run
    async def run(self) -> str:
        # Activity 1
        result1 = await workflow.execute_activity(
            step_one,
            start_to_close_timeout=timedelta(seconds=5),
        )
        workflow.logger.info(f"Step 1 result: {result1}")

        # Durable timer — survives Worker crashes
        workflow.logger.info("Sleeping for 10 seconds...")
        await asyncio.sleep(10)

        # Activity 2
        result2 = await workflow.execute_activity(
            step_two,
            start_to_close_timeout=timedelta(seconds=5),
        )
        workflow.logger.info(f"Step 2 result: {result2}")

        return f"{result1} | {result2}"


# --- Worker ---

async def run_worker():
    client = await Client.connect("localhost:7233", namespace="default")
    worker = Worker(
        client,
        task_queue="durable-execution-tasks",
        workflows=[DurableExecutionWorkflow],
        activities=[step_one, step_two],
    )
    print("Starting worker... Press Ctrl+C to stop.")
    await worker.run()


# --- Starter ---

async def run_starter():
    client = await Client.connect("localhost:7233")
    handle = await client.start_workflow(
        DurableExecutionWorkflow.run,
        id="durable-execution-demo",
        task_queue="durable-execution-tasks",
    )
    print(f"Started workflow. Workflow ID: {handle.id}")
    print("Tip: Kill the Worker during the 10s sleep, then restart it.")
    result = await handle.result()
    print(f"Final result: {result}")


# --- Main ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python exercise_05_durable_execution.py worker")
        print("  python exercise_05_durable_execution.py starter")
        sys.exit(1)

    command = sys.argv[1]

    if command == "worker":
        asyncio.run(run_worker())
    elif command == "starter":
        asyncio.run(run_starter())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
