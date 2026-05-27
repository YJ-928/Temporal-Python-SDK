import asyncio
import uuid

from temporalio.client import Client

from workflows import InfiniteRetryWorkflow, FiniteRetryWorkflow, GREET_TASK_QUEUE, FAREWELL_TASK_QUEUE

async def main():

    # Create and connect client to temporal server
    client = await Client.connect("localhost:7233")

    # Start both workflows simultaneously
    greeting_result, farewell_result = await asyncio.gather(
        client.execute_workflow(
            InfiniteRetryWorkflow,
            id=f"Greet-User-{uuid.uuid4()}",
            task_queue=GREET_TASK_QUEUE
        ),
        client.execute_workflow(
            FiniteRetryWorkflow,
            id=f"Farewell-User-{uuid.uuid4()}",
            task_queue=FAREWELL_TASK_QUEUE
        ),
        return_exceptions=True
    )

    print(f"GREETING WORKFLOW RESULT: {greeting_result}")
    print(f"FAREWELL WORKFLOW RESULT: {farewell_result}")


if __name__ == "__main__":
    asyncio.run(main())