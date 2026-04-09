import asyncio

from temporalio.client import Client

from workflow import LongRunningWorkflow, TASK_QUEUE

async def main() -> None:
    """To create and connect client to Temporal server and execute workflow using worker"""

    # Connect client to Temporal server
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        LongRunningWorkflow.calculate,
        id="long-running-workflow",
        task_queue=TASK_QUEUE
    )

    return result


if __name__ == "__main__":
    asyncio.run(main())