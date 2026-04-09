from datetime import timedelta
from temporalio import workflow

@workflow.defn
class ParentWorkflow:

    @workflow.run()
    async def process_file(self):
        pass

    @workflow.run()
    async def process_video(self):
        pass

    