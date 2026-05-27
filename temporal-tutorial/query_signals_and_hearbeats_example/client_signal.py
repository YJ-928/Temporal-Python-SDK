import asyncio

from temporalio.client import Client

from starter import WORKFLOW_ID
from workflow import CounterWorkflow

async def main() -> None:
    """Function to simulate external client signal to workflow"""

    # Create a client and connect to temporal server
    client = await Client.connect("localhost:7233")

    # Create a workflow handle using workflow id
    handle = client.get_workflow_handle(WORKFLOW_ID)

    # Send the signal to workflow
    await handle.signal(CounterWorkflow.stop_counter_func)

if __name__ == "__main__":
    asyncio.run(main())
