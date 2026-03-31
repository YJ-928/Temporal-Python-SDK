"""
Exercise 03 — Farewell Workflow

Objective:
    Extend a greeting Workflow to also call a farewell Activity.

Concepts:
    - Class-based Activities with dependency injection
    - Executing multiple Activities in a Workflow
    - workflow.execute_activity_method()
    - aiohttp for HTTP calls

Instructions:
    1. Start Temporal dev server: temporal server start-dev
    2. Start the microservice (provides translation):
       python -c "
       from flask import Flask, request
       app = Flask(__name__)
       @app.route('/get-spanish-greeting')
       def greet():
           name = request.args.get('name', 'World')
           return f'¡Hola, {name}!'
       @app.route('/get-spanish-farewell')
       def farewell():
           name = request.args.get('name', 'World')
           return f'¡Adiós, {name}!'
       app.run(port=9999)
       "
    3. Run the Worker:   python exercise_03_farewell_workflow.py worker
    4. Run the Starter:  python exercise_03_farewell_workflow.py starter Maria

Expected output:
    Result: ¡Hola, Maria!
    ¡Adiós, Maria!
"""

import asyncio
import sys
import urllib.parse
from datetime import timedelta

import aiohttp
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker


# --- Activities ---

class TranslateActivities:
    """Activities that call the translation microservice."""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    @activity.defn
    async def greet_in_spanish(self, name: str) -> str:
        return await self._call_service("get-spanish-greeting", name)

    @activity.defn
    async def farewell_in_spanish(self, name: str) -> str:
        return await self._call_service("get-spanish-farewell", name)

    async def _call_service(self, endpoint: str, name: str) -> str:
        url = f"http://localhost:9999/{endpoint}?name={urllib.parse.quote(name)}"
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()


# --- Workflow ---

with workflow.unsafe.imports_passed_through():
    pass  # Activities imported above in same file for exercise simplicity


@workflow.defn
class GreetSomeone:
    """Workflow that greets and says farewell in Spanish."""

    @workflow.run
    async def run(self, name: str) -> str:
        greeting = await workflow.execute_activity_method(
            TranslateActivities.greet_in_spanish,
            name,
            start_to_close_timeout=timedelta(seconds=5),
        )

        farewell = await workflow.execute_activity_method(
            TranslateActivities.farewell_in_spanish,
            name,
            start_to_close_timeout=timedelta(seconds=5),
        )

        return f"{greeting}\n{farewell}"


# --- Worker ---

async def run_worker():
    client = await Client.connect("localhost:7233", namespace="default")

    async with aiohttp.ClientSession() as session:
        activities = TranslateActivities(session)
        worker = Worker(
            client,
            task_queue="greeting-tasks",
            workflows=[GreetSomeone],
            activities=[activities.greet_in_spanish, activities.farewell_in_spanish],
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
        print("  python exercise_03_farewell_workflow.py worker")
        print("  python exercise_03_farewell_workflow.py starter <name>")
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
