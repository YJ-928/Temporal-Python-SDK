"""
Exercise 04 — Finale Workflow

Objective:
    Create a Workflow that generates a certificate using an Activity
    referenced by name (string-based Activity execution).

Concepts:
    - workflow.execute_activity() with a string Activity name
    - Workflow IDs with business meaning
    - Temporal integration patterns

Instructions:
    1. Start Temporal dev server: temporal server start-dev
    2. Run the Worker:   python exercise_04_finale_workflow.py worker
    3. Run the Starter:  python exercise_04_finale_workflow.py starter "Jane Doe"

Expected output:
    Result: Certificate generated for Jane Doe at /tmp/certificate_jane_doe.pdf
"""

import asyncio
import sys
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


# --- Activity ---

@activity.defn
async def create_pdf(name: str) -> str:
    """Simulates generating a PDF certificate."""
    activity.logger.info(f"Creating certificate for: {name}")
    safe_name = name.lower().replace(" ", "_")
    file_path = f"/tmp/certificate_{safe_name}.pdf"
    activity.logger.info(f"Certificate created at: {file_path}")
    return f"Certificate generated for {name} at {file_path}"


# --- Workflow ---

@workflow.defn
class CertificateGeneratorWorkflow:
    """Workflow that generates a course completion certificate."""

    @workflow.run
    async def run(self, name: str) -> str:
        result = await workflow.execute_activity(
            create_pdf,
            name,
            start_to_close_timeout=timedelta(seconds=5),
        )
        return result


# --- Worker ---

async def run_worker():
    client = await Client.connect("localhost:7233", namespace="default")
    worker = Worker(
        client,
        task_queue="generate-certificate-taskqueue",
        workflows=[CertificateGeneratorWorkflow],
        activities=[create_pdf],
    )
    print("Starting worker... Press Ctrl+C to stop.")
    await worker.run()


# --- Starter ---

async def run_starter(name: str):
    client = await Client.connect("localhost:7233")
    handle = await client.start_workflow(
        CertificateGeneratorWorkflow.run,
        name,
        id="generate-certificate-workflow",
        task_queue="generate-certificate-taskqueue",
    )
    print(f"Started workflow. Workflow ID: {handle.id}, RunID: {handle.result_run_id}")
    result = await handle.result()
    print(f"Result: {result}")


# --- Main ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python exercise_04_finale_workflow.py worker")
        print('  python exercise_04_finale_workflow.py starter "Jane Doe"')
        sys.exit(1)

    command = sys.argv[1]

    if command == "worker":
        asyncio.run(run_worker())
    elif command == "starter":
        name = sys.argv[2] if len(sys.argv) > 2 else "Student"
        asyncio.run(run_starter(name))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
