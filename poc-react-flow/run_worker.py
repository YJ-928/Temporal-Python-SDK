import asyncio
import concurrent.futures
from temporalio.client import Client
from temporalio.worker import Worker

from activities.activity import execute_agent, say_hello


async def main():
    # Create client connected to server at the given address
    client = await Client.connect("localhost:7233")

    # Run the worker (execute_agent is async; say_hello is sync)
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as activity_executor:
        worker = Worker(
            client,
            task_queue="activity_queue",
            activities=[execute_agent, say_hello],
            activity_executor=activity_executor,
        )
        await worker.run()

if __name__ == "__main__":
    asyncio.run(main())