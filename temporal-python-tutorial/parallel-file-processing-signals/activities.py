from asyncio import sleep
from temporalio import activity

@activity.defn
async def process_file(file_id: int) -> str:
    """Activity to simulate file processing using the file_id as input"""
    activity.logger.info(f"Starting processing for file with ID: {file_id}...")
    for i in range(10,100,10):
        await sleep(1)
        activity.heartbeat(f"file processed: {i}%")
    return f"File {file_id} processed successfully"