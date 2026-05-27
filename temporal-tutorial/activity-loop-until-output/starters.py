import asyncio

from temporalio.client import Client

from workflows import PasswordCrackingWorkflow, TASK_QUEUE


async def main() -> None:
    user_input = await asyncio.to_thread(input, "Enter 3-digit PIN to crack (digits 0-9): ")
    pin = user_input.strip()

    if len(pin) != 3 or not pin.isdigit():
        print("Error: PIN must be exactly 3 digits (0-9).")
        return

    client = await Client.connect("localhost:7233")

    print(f"Starting PinCrackingWorkflow for PIN '{pin}'")

    result = await client.execute_workflow(
        PasswordCrackingWorkflow.crack_user_password,
        pin,
        id="password-cracking-workflow",
        task_queue=TASK_QUEUE,
    )

    print(f"Workflow completed! Cracked PIN: {result}")


if __name__ == "__main__":
    asyncio.run(main())
