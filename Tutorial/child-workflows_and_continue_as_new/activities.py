import asyncio
from temporalio import activity

class ActivityClass:

    @activity.defn
    async def file_processor(self) -> None:
        activity.heartbeat("File processing initiated...")
        for i in range(10,100,10):
            activity.heartbeat(f"File Processing Progress: {i}%")
            await asyncio.sleep(1)
        activity.heartbeat("File processing completed...")

    @activity.defn
    async def video_processor(self) -> None:
        activity.heartbeat("Video processing initiated...")
        for i in range(10,100,5):
            activity.heartbeat(f"Video Processing Progress: {i}%")
            await asyncio.sleep(2)
        activity.heartbeat("Video processing completed...")

