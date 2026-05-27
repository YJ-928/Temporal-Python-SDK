import asyncio
from temporalio.client import Client

from workflows import FileProcessorWorkflow, TASK_QUEUE

WORKFLOW_ID = "file-processor-workflow"


async def main() -> None:
    client = await Client.connect("localhost:7233")

    print("Starting File Processor Workflow...")

    await client.start_workflow(
        FileProcessorWorkflow.run,
        id=WORKFLOW_ID,
        task_queue=TASK_QUEUE,
    )

    print("Workflow started!")


if __name__ == "__main__":
    asyncio.run(main())
