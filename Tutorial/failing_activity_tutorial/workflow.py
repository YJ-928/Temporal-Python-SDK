from temporalio import workflow

from activity import random_fail_task

@workflow.defn
class RandomFailWorkflow:
    @workflow.run
    async def task(self) -> bool:
        return await workflow.execute_activity(
            random_fail_task,
            schedule_to_start_timeout=2
        )