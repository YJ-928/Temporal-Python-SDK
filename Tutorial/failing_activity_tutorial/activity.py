import random
from temporalio import activity

@activity.defn
async def random_fail_task():
    if random.random() < 0.7:
        raise Exception("Failed")
    return "Success"