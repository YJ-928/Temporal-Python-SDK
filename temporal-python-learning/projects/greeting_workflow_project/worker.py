"""
Greeting Workflow — Worker

Registers the GreetingWorkflow and greet Activity with the Worker,
then polls the 'greeting-tasks' Task Queue.

Usage:
    python worker.py
"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from greet_activity import greet
from greeting_workflow import GreetingWorkflow, TASK_QUEUE


async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[GreetingWorkflow],
        activities=[greet],
    )
    print(f"Greeting worker started on task queue '{TASK_QUEUE}'. Ctrl-C to stop.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
