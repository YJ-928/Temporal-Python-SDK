"""
Exercise 01 — Hello Workflow

Objective:
    Create a simple Temporal Workflow that returns a greeting message.

Concepts:
    - @workflow.defn and @workflow.run decorators
    - Starting a Worker
    - Running a Workflow via a starter

Instructions:
    1. Start the Temporal dev server: temporal server start-dev
    2. Run the Worker:   python exercise_01_hello_workflow.py worker
    3. Run the Starter:  python exercise_01_hello_workflow.py starter Alice

Expected output:
    Result: Hello, Alice!
"""

import asyncio
import sys

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker


# --- Workflow Definition ---

@workflow.defn
class GreetSomeone:
    """A simple Workflow that returns a greeting."""

    @workflow.run
    async def run(self, name: str) -> str:
        return f"Hello, {name}!"


# --- Worker ---

async def run_worker():
    client = await Client.connect("localhost:7233", namespace="default")
    worker = Worker(
        client,
        task_queue="greeting-tasks",
        workflows=[GreetSomeone],
    )
    print("Starting worker... Press Ctrl+C to stop.")
    await worker.run()


# --- Starter ---

async def run_starter(name: str):
    client = await Client.connect("localhost:7233")
    handle = await client.start_workflow(
        GreetSomeone.run,
        name,
        id="greeting-workflow",
        task_queue="greeting-tasks",
    )
    print(f"Started workflow. Workflow ID: {handle.id}, RunID: {handle.result_run_id}")
    result = await handle.result()
    print(f"Result: {result}")


# --- Main ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python exercise_01_hello_workflow.py worker")
        print("  python exercise_01_hello_workflow.py starter <name>")
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
