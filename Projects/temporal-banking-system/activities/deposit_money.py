from asyncio import sleep
from temporalio import activity

@activity.defn
async def credit_money(balance:float, amount:float) -> float:
    activity.heartbeat(f"Initiating deposit of {amount} rupees...")
    await sleep(1)

    activity.heartbeat("Verifying account details...")
    await sleep(2)

    activity.heartbeat("Contacting payment gateway...")
    await sleep(2)

    activity.heartbeat(f"Processing credit of {amount} rupees to account...")
    await sleep(2)

    balance += amount

    activity.heartbeat("Updating account records...")
    await sleep(1)

    activity.heartbeat("Deposit transaction completed successfully!")
    print(f"Updated balance after credit: {balance}")
    return balance
