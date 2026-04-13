import asyncio
import random
from temporalio.client import Client

from clients import WORKFLOW_ID
from workflows import FileProcessorWorkflow

async def send_signal(handle, file_id) -> None:
    await handle.signal(
        FileProcessorWorkflow.process_file_signal,
        file_id
    )
    print(f"Sent signal for file {file_id}")


async def main() -> None:
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(WORKFLOW_ID)

    tasks = []

    for _ in range(20):
        file_id = random.randint(1, 100)
        tasks.append(send_signal(handle, file_id))

    # Send all signals concurrently
    await asyncio.gather(*tasks)

    print("All signals sent in parallel!")


if __name__ == "__main__":
    asyncio.run(main())