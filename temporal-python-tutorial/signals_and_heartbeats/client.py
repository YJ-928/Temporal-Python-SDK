import asyncio

from temporalio.client import Client

from workflow import SignalWorkflow, TASK_QUEUE

async def main():
    """Starter program to start workflow and await signal"""

    # Create and connect client to Temporal server
    client = await Client.connect("localhost:7233")

    result = await client.execute_workflow(
        SignalWorkflow,
        id="signal-heartbeats-1",
        task_queue=TASK_QUEUE
    )

    return result

if __name__ == "__main__":
    asyncio.run(main())