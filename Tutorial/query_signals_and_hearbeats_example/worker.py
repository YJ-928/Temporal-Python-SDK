import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from workflow import CounterWorkflow, TASK_QUEUE
from activity import incrementer

async def main() -> None:
    """Function to create and assign worker to taskqueue"""

    # Await client
    client = await Client.connect("localhost:7233")

    # Create worker and assign to poll the task-queue
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[CounterWorkflow],
        activities=[incrementer]
    )

    # Start the worker
    print("Worker started...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())