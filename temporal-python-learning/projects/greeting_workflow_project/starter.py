"""
Greeting Workflow — Starter

Starts the GreetingWorkflow with a name obtained from the command line
(or a default) and prints the result.

Usage:
    python starter.py
    python starter.py Alice
"""

import asyncio
import sys

from temporalio.client import Client

from greeting_workflow import GreetingWorkflow, TASK_QUEUE


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    client = await Client.connect("localhost:7233")
    result = await client.execute_workflow(
        GreetingWorkflow.run,
        name,
        id=f"greeting-{name.lower()}",
        task_queue=TASK_QUEUE,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
