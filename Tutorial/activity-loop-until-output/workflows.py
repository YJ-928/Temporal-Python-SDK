from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from activities import generate_password, validate_password

TASK_QUEUE = "password-cracking-task-queue"

@workflow.defn
class PasswordCrackingWorkflow:
    """Workflow to simulate user password cracking using interdependent activity loop"""

    def __init__(self) -> None:
        self._stop_requested: bool = False
        self._current_attempt: int = 0
        self._current_generated: str = ""
        self._override_password: str | None = None

    @workflow.signal
    def stop(self) -> None:
        """Signal to manually stop the workflow gracefully"""
        workflow.logger.info("Stop signal received, halting after current attempt")
        self._stop_requested = True

    @workflow.query
    def get_progress(self) -> dict:
        """Query to check current attempt number and last generated password"""
        return {
            "attempt": self._current_attempt,
            "current_generated_password": self._current_generated,
        }

    @workflow.update
    def set_override_password(self, password: str) -> str:
        """Update to inject a specific password instead of the randomly generated one"""
        self._override_password = password.lower()
        workflow.logger.info(f"Override password set to: {self._override_password}")
        return f"Override password set to: {self._override_password}"

    @workflow.run
    async def crack_user_password(self, password: str) -> str:
        MAX_ATTEMPTS = 500

        workflow.logger.info(f"Target PIN: '{password}'")

        while self._current_attempt < MAX_ATTEMPTS:
            if self._stop_requested:
                workflow.logger.info("Workflow stopped by signal")
                raise ApplicationError("Workflow manually stopped via signal", non_retryable=True)

            self._current_attempt += 1
            workflow.logger.info(
                f"Password Crack Attempt: {self._current_attempt}/{MAX_ATTEMPTS}"
            )

            # Activity 1: generate a password with matching letter/digit composition
            # await workflow.sleep(3)
            if self._override_password is not None:
                self._current_generated = self._override_password
                self._override_password = None
                workflow.logger.info(
                    f"Using override password: {self._current_generated}"
                )
            else:
                self._current_generated = await workflow.execute_activity(
                    generate_password,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=5),
                        maximum_attempts=3,
                    ),
                )

            # Activity 2: compare generated password against the target
            # await workflow.sleep(3)
            passwords_match = await workflow.execute_activity(
                validate_password,
                args=[self._current_generated, password],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_attempts=3,
                ),
            )

            if passwords_match:
                workflow.logger.info(
                    f"Password cracked after {self._current_attempt} attempt(s): "
                    f"{self._current_generated}"
                )
                return self._current_generated

        raise ApplicationError(
            f"Failed to crack password after {MAX_ATTEMPTS} attempts, workflow failed.",
            non_retryable=True,
        )
