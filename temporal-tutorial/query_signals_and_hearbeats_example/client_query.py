import asyncio

from temporalio.client import Client

from starter import WORKFLOW_ID
from workflow import CounterWorkflow

async def main() -> str:
    """Function to simulate external client query to workflow"""

    while True:
        # Create a client and connect to temporal server
        client = await Client.connect("localhost:7233")

        # Create a handle using the client and workflow_id
        handle = client.get_workflow_handle(WORKFLOW_ID)

        # Query the workflow using the created handle
        count = await handle.query(CounterWorkflow.get_current_count)

        print(f"Recieved count from Workflow using query: {count}")
        return count

if __name__ == "__main__":
    asyncio.run(main())
