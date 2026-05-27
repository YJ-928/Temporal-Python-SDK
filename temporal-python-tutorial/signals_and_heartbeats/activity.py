import asyncio
import random
from typing import Literal
from temporalio import activity

@activity.defn
async def file_processor() -> Literal['File processed successfully']:
    """A file processor simulation that returns hearbeats"""

    for i in range(1,999):
        random_int = random.randint(1,100)
        if random_int <= 99:
            print(f"heartbeats :{i}")
            activity.heartbeat(i)
        else:
            activity.heartbeat(random_int)
            print("Heartbeat stopped !!!")
            await asyncio.sleep(5)

    return "File processed successfully"