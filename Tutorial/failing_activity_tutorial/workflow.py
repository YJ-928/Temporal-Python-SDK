from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activity import random_fail_task


@workflow.defn
class RandomFailWorkflow:

    @workflow.run
    async def task(self) -> str:

        result = await workflow.execute_activity(
            random_fail_task,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=5
            ),
        )

        return result