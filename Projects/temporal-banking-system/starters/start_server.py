import asyncio
import sys
import os

from temporalio.client import Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from workflows.banking_workflow import BankServerWorkflow, TASK_QUEUE

WORKFLOW_EXECUTION_ID = "banking-server-01"

async def main() -> None:
    client = await Client.connect("localhost:7233")
    result = await client.execute_workflow(
        BankServerWorkflow.banking_server,
        id=WORKFLOW_EXECUTION_ID,
        task_queue=TASK_QUEUE
    )
    return result

if __name__ == "__main__":
    asyncio.run(main())
