import asyncio

from agents.pydantic import parse_intent


async def run():
    result = await parse_intent("I need a hotel in Paris for next week")
    print(result.model_dump())  # e.g. {"type": "HOTEL"}


if __name__ == "__main__":
    asyncio.run(run())