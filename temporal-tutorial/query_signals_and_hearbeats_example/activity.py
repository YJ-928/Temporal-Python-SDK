from asyncio import sleep
from temporalio import activity

@activity.defn
async def incrementer(value: int) -> int:
    """An incrementer which takes a value and increases it by 1"""
    activity.heartbeat(f"Recieved Value: {value}")
    await sleep(4)
    result = value + 1
    await sleep(1)
    activity.heartbeat(f"Incremented Value: {result}")
    await sleep(4)
    return result

