"""
Demo POC — Child Workflows
==========================
Standalone child workflows spawned by the main TemporalShowcaseWorkflow during
the Media Processor phase.  Each wraps a single media-processing activity so it
gets its own independent execution context, history, and retry scope.

Origin tutorial: child-workflows_and_continue_as_new
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import process_file_media, process_video_media


# Both child workflows share the same task queue as the parent so a single
# worker can handle everything in this demo.
TASK_QUEUE = "temporal-showcase-queue"


@workflow.defn
class FileProcessingChildWorkflow:
    """
    Child workflow that runs the file-media processing activity.
    Spawned in parallel with VideoProcessingChildWorkflow by the parent.
    """

    @workflow.run
    async def run(self) -> str:
        result = await workflow.execute_activity(
            process_file_media,
            start_to_close_timeout=timedelta(seconds=60),
            heartbeat_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            ),
        )
        workflow.logger.info(f"FileProcessingChildWorkflow done: {result}")
        return result


@workflow.defn
class VideoProcessingChildWorkflow:
    """
    Child workflow that runs the video processing activity.
    Spawned in parallel with FileProcessingChildWorkflow by the parent.
    """

    @workflow.run
    async def run(self) -> str:
        result = await workflow.execute_activity(
            process_video_media,
            start_to_close_timeout=timedelta(seconds=60),
            heartbeat_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            ),
        )
        workflow.logger.info(f"VideoProcessingChildWorkflow done: {result}")
        return result
