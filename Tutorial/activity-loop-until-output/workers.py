import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from workflows import PasswordCrackingWorkflow, TASK_QUEUE
from activities import generate_password, validate_password


async def main() -> None:
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[PasswordCrackingWorkflow],
        activities=[generate_password, validate_password],
    )

    print(f"Worker started on task queue: {TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
