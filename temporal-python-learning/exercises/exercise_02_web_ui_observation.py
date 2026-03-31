"""
Exercise 02 — Web UI Observation

Objective:
    Run a Workflow and observe its execution in the Temporal Web UI.

Concepts:
    - Temporal Web UI at http://localhost:8233
    - Workflow status (Running, Completed, Failed)
    - Event history inspection
    - Activity input/output viewing

Instructions:
    1. Start Temporal dev server:    temporal server start-dev
    2. Start the Worker:             python exercise_02_web_ui_observation.py worker
    3. Run the Starter:              python exercise_02_web_ui_observation.py starter Alice
    4. Open the Web UI:              http://localhost:8233
    5. Find the Workflow "web-ui-demo-workflow" in the list
    6. Click on it and explore:
       - Summary tab (ID, type, status)
       - Event History tab (every step of execution)
       - Activity input and output

Questions to answer:
    - What events appear in the history?
    - What was the Activity input?
    - What was the Activity output?
    - How long did the Activity take?
"""

import asyncio
import sys
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


# --- Activity ---

@activity.defn
async def greet_with_timestamp(name: str) -> str:
    """Activity that generates a detailed greeting."""
    activity.logger.info(f"greet_with_timestamp invoked with name: {name}")
    greeting = f"Hello, {name}! Welcome to Temporal."
    activity.logger.info(f"greet_with_timestamp completed: {greeting}")
    return greeting


# --- Workflow ---

@workflow.defn
class WebUIDemoWorkflow:
    """Workflow designed for Web UI observation."""

    @workflow.run
    async def run(self, name: str) -> str:
        workflow.logger.info(f"WebUIDemoWorkflow started with name: {name}")

        greeting = await workflow.execute_activity(
            greet_with_timestamp,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )

        workflow.logger.info(f"WebUIDemoWorkflow completed with result: {greeting}")
        return greeting


# --- Worker ---

async def run_worker():
    client = await Client.connect("localhost:7233", namespace="default")
    worker = Worker(
        client,
        task_queue="web-ui-demo-tasks",
        workflows=[WebUIDemoWorkflow],
        activities=[greet_with_timestamp],
    )
    print("Starting worker... Press Ctrl+C to stop.")
    print("Open the Web UI at http://localhost:8233 to observe workflows.")
    await worker.run()


# --- Starter ---

async def run_starter(name: str):
    client = await Client.connect("localhost:7233")
    handle = await client.start_workflow(
        WebUIDemoWorkflow.run,
        name,
        id="web-ui-demo-workflow",
        task_queue="web-ui-demo-tasks",
    )
    print(f"Started workflow. Workflow ID: {handle.id}")
    print(f"Open http://localhost:8233 and find workflow '{handle.id}'")

    result = await handle.result()
    print(f"Result: {result}")


# --- Main ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python exercise_02_web_ui_observation.py worker")
        print("  python exercise_02_web_ui_observation.py starter <name>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "worker":
        asyncio.run(run_worker())
    elif command == "starter":
        name = sys.argv[2] if len(sys.argv) > 2 else "World"
        asyncio.run(run_starter(name))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
