import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activity import file_processor
from workflow import SignalWorkflow, TASK_QUEUE

async def main() -> None:
    """To create and assign worker to given workflow and taskqueue"""

    # Connect to client
    client = await Client.connect("localhost:7233")

    # Create and assign worker to poll taskqueue
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[SignalWorkflow],
        activities=[file_processor]
    )

    # Run the worker
    print("Worker started...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())