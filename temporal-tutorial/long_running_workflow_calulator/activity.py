import asyncio
from random import randint
from temporalio import activity

class Calculator:
    """Class containing calculator operation functions as activity definitions"""

    @activity.defn
    async def generate_value(self) -> int:
        value = randint(1,10000)
        activity.heartbeat(f"Generated Value: {value}")
        await asyncio.sleep(1)
        return value
        
    @activity.defn
    async def addition(self, value1, value2) -> str:
        activity.heartbeat("Adding...")
        await asyncio.sleep(1)
        return f"Addition of {value1} and {value2} = {value1 + value2}"
    
    @activity.defn
    async def subtraction(self, value1, value2) -> str:
        activity.heartbeat("Subtracting...")
        await asyncio.sleep(1)
        return f"Subtraction of {value1} and {value2} = {value1 - value2}"
    
    @activity.defn
    async def multiplication(self, value1, value2) -> str:
        activity.heartbeat("Multiplying...")
        await asyncio.sleep(1)
        return f"Multiplication of {value1} and {value2} = {value1 * value2}"
    
    @activity.defn
    async def integer_division(self, value1, value2) -> str:
        activity.heartbeat("Dividing...")
        await asyncio.sleep(1)
        return f"Integer Division of {value1} and {value2} = {value1 // value2}"
