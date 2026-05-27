from temporalio import activity

@activity.defn
async def Greet(name:str) -> str:
    return f"Hello {name}"