import asyncio
import sys
import os

from temporalio.client import Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from workflows.banking_workflow import BankServerWorkflow

WORKFLOW_EXECUTION_ID = "banking-server-01"

MENU = """
========================================
       Banking System Admin CLI
========================================
  1. Check Balance         (Query)
  2. Deposit Money         (Update)
  3. Withdraw Money        (Update)
  4. Freeze Account        (Signal)
  5. Unfreeze Account      (Signal)
  6. Stop Bank Server      (Signal)
  0. Exit
========================================
"""

async def main() -> None:
    client = await Client.connect("localhost:7233")
    handle = client.get_workflow_handle(WORKFLOW_EXECUTION_ID)

    print(f"Connected to workflow: {WORKFLOW_EXECUTION_ID}")

    while True:
        print(MENU)
        choice = (await asyncio.to_thread(input, "Enter option: ")).strip()

        match choice:
            case "1":
                result = await handle.query(BankServerWorkflow.check_balance)
                print(f"\n  Balance: {result}")

            case "2":
                try:
                    amount = float((await asyncio.to_thread(input, "  Enter amount to deposit: ")).strip())
                    result = await handle.execute_update(BankServerWorkflow.add_money_to_account, amount)
                    print(f"\n  Updated Balance after deposit: {result}")
                except ValueError:
                    print("  Invalid amount. Please enter a number.")

            case "3":
                try:
                    amount = float((await asyncio.to_thread(input, "  Enter amount to withdraw: ")).strip())
                    result = await handle.execute_update(BankServerWorkflow.remove_money_from_account, amount)
                    print(f"\n  Updated Balance after withdrawal: {result}")
                except ValueError:
                    print("  Invalid amount. Please enter a number.")

            case "4":
                await handle.signal(BankServerWorkflow.freeze_account)
                print("\n  Account has been frozen.")

            case "5":
                await handle.signal(BankServerWorkflow.unfreeze_account)
                print("\n  Account has been unfrozen.")

            case "6":
                confirm = (await asyncio.to_thread(input, "  Are you sure you want to stop the bank server? (yes/no): ")).strip().lower()
                if confirm == "yes":
                    await handle.signal(BankServerWorkflow.stop_bank_server)
                    print("\n  Stop signal sent. Bank server will shut down.")
                    break
                else:
                    print("  Cancelled.")

            case "0":
                print("\n  Exiting admin CLI.")
                break

            case _:
                print("\n  Invalid option. Please choose from the menu.")

if __name__ == "__main__":
    asyncio.run(main())
