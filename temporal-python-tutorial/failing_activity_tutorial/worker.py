import asyncio
from temporalio.worker import Worker
from temporalio.client import Client

from workflow import RandomFailWorkflow
from activity import random_fail_task


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="random-fail-task-queue",
        workflows=[RandomFailWorkflow],
        activities=[random_fail_task],
    )

    print("Worker Started")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())