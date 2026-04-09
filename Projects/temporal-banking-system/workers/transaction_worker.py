import asyncio
import sys
import os

from temporalio.client import Client
from temporalio.worker import Worker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from workflows.banking_workflow import BankServerWorkflow, TASK_QUEUE
from activities.deposit_money import credit_money
from activities.withdraw_money import debit_money

async def main() -> None:
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[BankServerWorkflow],
        activities=[credit_money, debit_money]
    )
    print("Worker started...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
