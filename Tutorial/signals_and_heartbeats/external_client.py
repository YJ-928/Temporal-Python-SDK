import asyncio

from temporalio.client import Client

from workflow import SignalWorkflow

async def main() -> None:
    """External client to send signal to running workflow"""

    client = await Client.connect("localhost:7233")

    handle = client.get_workflow_handle("signal-heartbeats-1")

    await handle.signal(SignalWorkflow.request_result)

if __name__ == "__main__":
    asyncio.run(main())
