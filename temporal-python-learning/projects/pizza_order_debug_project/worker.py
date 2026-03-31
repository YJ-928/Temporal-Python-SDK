"""
Pizza Order Debug Project — Worker

Usage:
    python worker.py
"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from pizza_activities import get_distance, send_bill
from pizza_workflow import PizzaOrderWorkflow, TASK_QUEUE


async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[PizzaOrderWorkflow],
        activities=[get_distance, send_bill],
    )
    print(f"Pizza worker started on '{TASK_QUEUE}'. Ctrl-C to stop.")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
