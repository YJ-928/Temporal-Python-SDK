from asyncio import sleep
from temporalio import activity

@activity.defn
async def debit_money(balance:float, amount:float) -> float:
    activity.heartbeat(f"Initiating withdrawal of {amount} rupees...")
    await sleep(1)

    activity.heartbeat("Verifying account details...")
    await sleep(2)

    activity.heartbeat("Checking available balance...")
    await sleep(1)

    activity.heartbeat(f"Processing debit of {amount} rupees from account...")
    await sleep(2)

    balance -= amount

    activity.heartbeat("Updating account records...")
    await sleep(1)

    activity.heartbeat("Withdrawal transaction completed successfully!")
    print(f"Updated balance after debit: {balance}")
    return balance
