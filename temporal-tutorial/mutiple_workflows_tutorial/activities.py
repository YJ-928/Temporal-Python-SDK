import aiohttp
from temporalio import activity

class UserActivities:
    """A activity class containing user greeting and farewell methods"""

    @activity.defn
    async def greet_user(self, name: str) -> str:
        """Activity method to greet user using fastapi service"""
        url = f"http://localhost:9999/greet?name={name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()

    @activity.defn
    async def farewell_user(self, name: str) -> str:
        """Activity method to farewell user using fastapi service"""
        url = f"http://localhost:9999/farewell?name={name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()
