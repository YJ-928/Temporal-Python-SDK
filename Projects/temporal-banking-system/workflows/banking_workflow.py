from datetime import timedelta
from typing import Literal
from temporalio import workflow
from temporalio.common import RetryPolicy

from activities import credit_money, debit_money

TASK_QUEUE = "Banking-System"
FROZEN_ACCOUNT_ERROR = "Account is Frozen, cannot access funds"

@workflow.defn
class BankServerWorkflow:
    """Workflow class to simulate complete flow of banking operations"""

    def __init__(self) -> None:
        self.account_balance = 0.0
        self.frozen_account = False
        self.stop_server = False

    @workflow.signal
    def stop_bank_server(self) -> None:
        self.stop_server = True

    @workflow.signal
    def freeze_account(self) -> None:
        self.frozen_account = True

    @workflow.signal
    def unfreeze_account(self) -> None:
        self.frozen_account = False

    @workflow.query
    def check_balance(self) -> float | Literal['Account is Frozen, cannot access funds']:
        if not self.frozen_account:
            return self.account_balance
        return FROZEN_ACCOUNT_ERROR
    
    async def add_money(self, amount: float) -> float:
        updated_balance = await workflow.execute_activity(
            credit_money,
            args=[self.account_balance, amount],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=1,
                maximum_attempts=3
            )
        )
        self.account_balance = updated_balance
        return self.account_balance
    
    async def remove_money(self, amount: float) -> float:
        updated_balance = await workflow.execute_activity(
            debit_money,
            args=[self.account_balance, amount],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=1,
                maximum_attempts=3
            )
        )
        self.account_balance = updated_balance
        return self.account_balance

    @workflow.update
    async def add_money_to_account(self, amount:float) -> float | Literal['Account is Frozen, cannot access funds']:
        if not self.frozen_account:
            balance = await self.add_money(amount)
            return balance
        return FROZEN_ACCOUNT_ERROR
    
    @workflow.update
    async def remove_money_from_account(self, amount:float) -> float | Literal['Account is Frozen, cannot access funds']:
        if not self.frozen_account:
            balance = await self.remove_money(amount)
            return balance
        return FROZEN_ACCOUNT_ERROR
    
    @workflow.run
    async def banking_server(self) -> str:
        while not self.stop_server:
            workflow.logger.info("Awaiting Signals, Queries or Updates...")
            await workflow.sleep(timedelta(seconds=5))
            workflow.logger.info(f"Current Account Balance: {self.account_balance}")
        
        return f"Bank account closed with balance: {self.account_balance}"
