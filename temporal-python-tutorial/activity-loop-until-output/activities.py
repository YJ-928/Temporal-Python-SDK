import random
import string

from temporalio import activity

@activity.defn
async def generate_password() -> str:
    """Generate a random 3-digit PIN using digits 0-9"""
    activity.heartbeat("Generating PIN...")
    activity.logger.info("Generating 3-digit PIN")
    return "".join(random.choices(string.digits, k=3))

@activity.defn
async def validate_password(generated_password: str, user_password: str) -> bool:
    """Activity to validate given passwords and return Boolean"""
    activity.heartbeat("Validating passwords...")
    # await sleep(2)
    if generated_password.lower() == user_password.lower():
        activity.logger.info("Password validated successfully")
        return True
    else:
        activity.logger.info("Password validation failed, incorrect generated password")
        return False
