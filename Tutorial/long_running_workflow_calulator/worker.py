import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activity import Calculator
from workflow import LongRunningWorkflow, TASK_QUEUE

async def main() -> None:
    """Create workers and assign them to poll task_queue"""

    # Await client
    client = await Client.connect("localhost:7233")

    # Instantiate activities class
    calculator = Calculator()

    # Create and assign worker
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[LongRunningWorkflow],
        activities=[
            calculator.generate_value,
            calculator.addition,
            calculator.subtraction,
            calculator.multiplication,
            calculator.integer_division,
        ]
    )

    # Start worker
    print("Worker started...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())