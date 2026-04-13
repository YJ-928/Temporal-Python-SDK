import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from activities import process_file
from workflows import FileProcessorWorkflow, TASK_QUEUE

async def main() -> None:
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[FileProcessorWorkflow],
        activities=[process_file],
        max_concurrent_activities=10, # worker can execute 10 activities in parallel
    )

    print("Worker started...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())