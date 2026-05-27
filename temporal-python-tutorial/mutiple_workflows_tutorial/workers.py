import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activities import UserActivities
from workflows import InfiniteRetryWorkflow, FiniteRetryWorkflow, GREET_TASK_QUEUE, FAREWELL_TASK_QUEUE

async def main():
    """Create and run workers"""

    # Connect to client
    client = await Client.connect("localhost:7233")

    # Instantiate activities class (required for instance methods)
    user_activities = UserActivities()

    # Create and assign worker to task queue
    greeting_worker = Worker(
        client,
        task_queue=GREET_TASK_QUEUE,
        workflows=[InfiniteRetryWorkflow],
        activities=[user_activities.greet_user]
    )

    # Create and assign worker to task queue
    farewell_worker = Worker(
        client,
        task_queue=FAREWELL_TASK_QUEUE,
        workflows=[FiniteRetryWorkflow],
        activities=[user_activities.farewell_user]
    )

    print("Starting both workers...")
    # Run both workers concurrently
    await asyncio.gather(greeting_worker.run(), farewell_worker.run())

if __name__ == "__main__":
    asyncio.run(main())