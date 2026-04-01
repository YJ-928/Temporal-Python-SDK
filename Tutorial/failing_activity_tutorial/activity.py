import random
from temporalio import activity

@activity.defn
async def random_fail_task():

    attempt = activity.info().attempt
    print(f"Running attempt {attempt}")

    if random.random() < 0.7:
        raise Exception("Random failure")

    return f"Success on attempt {attempt}"