import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from tutorial.workflows.say_hello import SayHelloWorkflow
from tutorial.activities.greet import Greet

async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="my-task-queue",
        workflows=[SayHelloWorkflow],
        activities=[Greet],
    )
    print("Worker Started")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())