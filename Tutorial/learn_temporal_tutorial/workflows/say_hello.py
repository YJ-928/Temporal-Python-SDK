from datetime import timedelta
from temporalio import workflow

from tutorial.activities.greet import Greet

@workflow.defn
class SayHelloWorkflow:
    @workflow.run
    async def run(self, name:str) -> str:
        return await workflow.execute_activity(
            Greet,
            name,
            schedule_to_close_timeout=timedelta(seconds=10),
        )