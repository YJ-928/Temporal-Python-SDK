import asyncio
import sys
import os

from temporalio.client import Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from workflows.banking_workflow import BankServerWorkflow

WORKFLOW_EXECUTION_ID = "banking-server-01"

async def deposit(handle, amount: float) -> None:
    result = await handle.execute_update(BankServerWorkflow.add_money_to_account, amount)
    print(f"Updated Balance after deposit: {result}")

async def withdraw(handle, amount: float) -> None:
    result = await handle.execute_update(BankServerWorkflow.remove_money_from_account, amount)
    print(f"Updated Balance after withdrawal: {result}")

async def main() -> None:
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(WORKFLOW_EXECUTION_ID)

    operation = str(await asyncio.to_thread(input, "Enter operation (deposit/withdraw): ").strip().lower())
    amount = float((await asyncio.to_thread(input, "Enter amount to withdraw: ")).strip())

    if operation == "deposit":
        await deposit(handle, amount)
    elif operation == "withdraw":
        await withdraw(handle, amount)
    else:
        print(f"Unknown operation: {operation}. Use 'deposit' or 'withdraw'.")

if __name__ == "__main__":
    asyncio.run(main())
