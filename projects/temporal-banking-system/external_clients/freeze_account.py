import asyncio
import sys
import os

from temporalio.client import Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from workflows.banking_workflow import BankServerWorkflow

WORKFLOW_EXECUTION_ID = "banking-server-01"

async def main() -> None:
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(WORKFLOW_EXECUTION_ID)

    await handle.signal(BankServerWorkflow.freeze_account)
    print("Signal sent: Account has been frozen.")

if __name__ == "__main__":
    asyncio.run(main())
