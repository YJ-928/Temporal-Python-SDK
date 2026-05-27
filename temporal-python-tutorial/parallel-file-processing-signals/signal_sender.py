import asyncio
import random
from temporalio.client import Client

from clients import WORKFLOW_ID
from workflows import FileProcessorWorkflow

async def main() -> None:
    client = await Client.connect("localhost:7233")

    handle = client.get_workflow_handle(WORKFLOW_ID)

    print("Sending signals...")

    # simulate 20 files
    for _ in range(20):
        file_id = random.randint(1, 100)

        await handle.signal(
            FileProcessorWorkflow.process_file_signal,
            file_id
        )

        print(f"Sent signal for file {file_id}")

    print("All signals sent!")


if __name__ == "__main__":
    asyncio.run(main())