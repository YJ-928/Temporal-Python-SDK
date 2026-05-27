import asyncio
import uuid

from temporalio.client import Client

from workflow import RandomFailWorkflow


async def main():
    client = await Client.connect("localhost:7233")

    response = await client.execute_workflow(
        RandomFailWorkflow.task,
        id=f"failing-workflow-demo-{uuid.uuid4()}",
        task_queue="random-fail-task-queue",
    )

    print(f"Workflow Result: {response}")


if __name__ == "__main__":
    asyncio.run(main())