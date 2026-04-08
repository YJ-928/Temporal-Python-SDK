import asyncio

from temporalio.client import Client

from workflow import LongRunningWorkflow

async def main() -> None:

    # Connect to Temporal Server
    client = await Client.connect("localhost:7233")

    # Fetch workflow id
    handle = client.get_workflow_handle("long-running-workflow")

    # Send signal
    print("Signal Sent to stop Long Running Workflow...")
    await handle.signal(LongRunningWorkflow.cancel_longrunning_workflow)

if __name__ == "__main__":
    asyncio.run(main())
