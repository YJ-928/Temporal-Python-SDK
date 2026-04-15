"""
Demo POC - Main Orchestrator Workflow
======================================
TemporalShowcaseWorkflow is a single long-running workflow that exercises every
major Temporal feature consolidated from all Tutorial sub-projects:

  Signals  ── start, pause, resume, stop, advance_phase, stop_counter,
               queue_file, override_pin
  Queries  ── get_status, get_phase_progress, get_results
  Updates  ── run_calculator  (execute an activity inline + return result)
               test_pin_match  (execute an activity inline + return result)
  Child WF ── FileProcessingChildWorkflow, VideoProcessingChildWorkflow (Phase 5)
  Retries  ── each phase uses its own RetryPolicy
  Heartbeat── every activity sends heartbeats (see activities.py)

Phase sequence
──────────────
  1  counter          - increments until stop_counter signal
  2  password_cracker - brute-forces a 3-digit PIN; supports override_pin signal
  3  file_processor   - processes files queued via queue_file signal in parallel
  4  calculator       - runs random math ops until advance_phase signal
  5  media_processor  - spawns two child workflows (file + video) in parallel
  6  resilience_test  - runs a randomly-failing activity to demonstrate retries

At any point:
  • pause / resume  - suspend and continue between await checkpoints
  • stop            - gracefully terminate and return whatever has completed so far
  • advance_phase   - skip / end the current phase (file_processor, calculator)
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

# Pure dataclass module - safe to import outside the sandbox
from shared import (
    StartInput,
    CalculatorInput,
    PinMatchInput,
    WorkflowStatus,
    CounterProgress,
    CrackerProgress,
    FileProcessorProgress,
    CalculatorProgress,
    MediaProgress,
    ResilienceProgress,
    PhaseProgress,
    CounterResult,
    CrackerResult,
    FileProcessorResult,
    CalculatorResult,
    MediaProcessorResult,
    ResilienceResult,
    ShowcaseResults,
)

with workflow.unsafe.imports_passed_through():
    from activities import (
        increment_counter,
        generate_pin,
        validate_pin,
        process_file,
        generate_operand,
        calculate,
        random_fail_task,
    )
    from child_workflows import FileProcessingChildWorkflow, VideoProcessingChildWorkflow

TASK_QUEUE = "temporal-showcase-queue"

# Ordered list of phases - used for status reporting and index bookkeeping.
PHASES = [
    "idle",
    "counter",
    "password_cracker",
    "file_processor",
    "calculator",
    "media_processor",
    "resilience_test",
    "completed",
]


@workflow.defn
class TemporalShowcaseWorkflow:
    """
    Long-running Temporal POC workflow that demonstrates signals, queries,
    workflow updates, child workflows, retry policies, and heartbeats in one
    cohesive flow.
    """

    # Init 

    def __init__(self) -> None:
        # Lifecycle
        self._started: bool = False
        self._paused: bool = False
        self._stopped: bool = False
        self._target_pin: str = ""

        # Phase navigation
        self._phase_index: int = 0      # index into PHASES
        self._advance_phase: bool = False

        # Phase 1 - Counter
        self._counter_value: int = 0
        self._counter_stop: bool = False

        # Phase 2 - Password Cracker
        self._crack_attempt: int = 0
        self._crack_current: str = ""
        self._crack_override: Optional[str] = None
        self._crack_cracked: bool = False

        # Phase 3 - Parallel File Processor
        self._file_queue: list[int] = []
        self._file_handles: list = []       # list of (file_id, ActivityHandle)
        self._files_processed: list[str] = []

        # Phase 4 - Calculator
        self._calc_results: list[str] = []

        # Phase 5 - Media Processor
        self._media_results: dict = {}

        # Phase 6 - Resilience Test
        self._resilience_result: str = ""

        # Typed accumulated results - one per phase, None until that phase completes
        self._result_counter: Optional[CounterResult] = None
        self._result_cracker: Optional[CrackerResult] = None
        self._result_file_processor: Optional[FileProcessorResult] = None
        self._result_calculator: Optional[CalculatorResult] = None
        self._result_media_processor: Optional[MediaProcessorResult] = None
        self._result_resilience_test: Optional[ResilienceResult] = None

    # Signals

    @workflow.signal
    def start(self, input: StartInput) -> None:
        """
        Kick off the showcase.  Must be the first signal sent after the workflow
        is started.  input.target_pin is the 3-digit PIN the cracker phase will
        try to guess.
        """
        if not self._started:
            self._target_pin = input.target_pin
            self._started = True
            workflow.logger.info(f"[signal] start - target PIN: {input.target_pin!r}")

    @workflow.signal
    def pause(self) -> None:
        """Pause the workflow between activity / sleep checkpoints."""
        self._paused = True
        workflow.logger.info("[signal] pause")

    @workflow.signal
    def resume(self) -> None:
        """Resume a previously paused workflow."""
        self._paused = False
        workflow.logger.info("[signal] resume")

    @workflow.signal
    def stop(self) -> None:
        """Gracefully stop the workflow and return all results collected so far."""
        self._stopped = True
        workflow.logger.info("[signal] stop")

    @workflow.signal
    def advance_phase(self) -> None:
        """
        Signal the current phase to finish and move on.
        Applies to: file_processor, calculator.
        """
        self._advance_phase = True
        workflow.logger.info("[signal] advance_phase")

    @workflow.signal
    def stop_counter(self) -> None:
        """End the counter phase and advance to the password cracker."""
        self._counter_stop = True
        workflow.logger.info("[signal] stop_counter")

    @workflow.signal
    def queue_file(self, file_id: int) -> None:
        """
        Add file_id to the parallel processing queue during the file_processor
        phase.  Can also be sent before the phase starts.
        """
        self._file_queue.append(file_id)
        workflow.logger.info(f"[signal] queue_file - file_id={file_id}")

    @workflow.signal
    def override_pin(self, pin: str) -> None:
        """
        Inject a specific PIN to be tested next in the password_cracker phase
        (mirrors the update handler from activity-loop-until-output tutorial).
        """
        self._crack_override = pin.lower()
        workflow.logger.info(f"[signal] override_pin - pin={pin!r}")

    # Queries

    @workflow.query
    def get_status(self) -> WorkflowStatus:
        """Return high-level workflow state."""
        return WorkflowStatus(
            phase=PHASES[self._phase_index] if self._phase_index < len(PHASES) else "completed",
            started=self._started,
            paused=self._paused,
            stopped=self._stopped,
            target_pin=self._target_pin,
        )

    @workflow.query
    def get_phase_progress(self) -> PhaseProgress:
        """Return the current phase name plus its specific in-flight metrics."""
        phase = PHASES[self._phase_index] if self._phase_index < len(PHASES) else "completed"
        progress = PhaseProgress(phase=phase)

        if phase == "counter":
            progress.counter = CounterProgress(
                counter_value=self._counter_value,
                stopped=self._counter_stop,
            )
        elif phase == "password_cracker":
            progress.cracker = CrackerProgress(
                attempt=self._crack_attempt,
                current_pin=self._crack_current,
                cracked=self._crack_cracked,
            )
        elif phase == "file_processor":
            progress.file_processor = FileProcessorProgress(
                queued=list(self._file_queue),
                in_flight=len(self._file_handles),
                completed=list(self._files_processed),
            )
        elif phase == "calculator":
            progress.calculator = CalculatorProgress(
                total_ops=len(self._calc_results),
                last_5=self._calc_results[-5:],
            )
        elif phase == "media_processor":
            progress.media = MediaProgress(
                file_result=self._media_results.get("file_processing", ""),
                video_result=self._media_results.get("video_processing", ""),
            )
        elif phase == "resilience_test":
            progress.resilience = ResilienceProgress(result=self._resilience_result)

        return progress

    @workflow.query
    def get_results(self) -> ShowcaseResults:
        """Return a typed snapshot of all accumulated phase results."""
        return self._build_result("in_progress")

    # Updates

    @workflow.update
    async def run_calculator(self, input: CalculatorInput) -> str:
        """
        Immediately execute a single calculator activity and return the result
        string.  Works from any phase.
        input.op must be one of: add, subtract, multiply, divide.
        """
        result = await workflow.execute_activity(
            calculate,
            args=[input.a, input.b, input.op],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            ),
        )
        workflow.logger.info(f"[update] run_calculator → {result}")
        return result

    @workflow.update
    async def test_pin_match(self, input: PinMatchInput) -> bool:
        """
        Immediately validate a PIN guess against a target via activity and
        return the boolean result.  Works from any phase.
        """
        matched = await workflow.execute_activity(
            validate_pin,
            args=[input.guess, input.target],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,
                maximum_attempts=3,
            ),
        )
        workflow.logger.info(f"[update] test_pin_match {input.guess!r} vs {input.target!r} → {matched}")
        return matched

    # Run

    @workflow.run
    async def run(self) -> ShowcaseResults:
        """
        Entry point.  Waits for the 'start' signal then runs through all phases
        in order, honouring pause / stop signals throughout.
        """
        workflow.logger.info("TemporalShowcaseWorkflow initialised - awaiting start signal")

        await workflow.wait_condition(lambda: self._started or self._stopped)
        if self._stopped:
            return self._build_result("stopped_before_start")

        workflow.logger.info(f"start signal received (target_pin={self._target_pin!r}) - entering Phase 1")

        # Phase 1
        self._phase_index = 1
        await self._run_counter()
        if self._stopped:
            return self._build_result("stopped")

        # Phase 2
        self._phase_index = 2
        await self._run_password_cracker()
        if self._stopped:
            return self._build_result("stopped")

        # Phase 3
        self._phase_index = 3
        await self._run_file_processor()
        if self._stopped:
            return self._build_result("stopped")

        # Phase 4
        self._phase_index = 4
        await self._run_calculator_phase()
        if self._stopped:
            return self._build_result("stopped")

        # Phase 5
        self._phase_index = 5
        await self._run_media_processor()
        if self._stopped:
            return self._build_result("stopped")

        # Phase 6
        self._phase_index = 6
        await self._run_resilience_test()

        self._phase_index = 7
        return self._build_result("completed")

    # Phase Runners

    async def _run_counter(self) -> None:
        """
        Phase 1 - Counter
        Increments a counter via the increment_counter activity on a 2-second
        cadence until the stop_counter signal (or global stop) is received.
        Demonstrates: signals controlling workflow loop, queries for live state.
        """
        workflow.logger.info("=== Phase 1: Counter ===")
        self._counter_stop = False
        self._counter_value = 0

        while not self._counter_stop and not self._stopped:
            await self._honour_pause()
            if self._stopped:
                break
            await workflow.sleep(timedelta(seconds=2))
            self._counter_value = await workflow.execute_activity(
                increment_counter,
                self._counter_value,
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=3),
                    backoff_coefficient=2.0,
                    maximum_attempts=5,
                ),
            )
            workflow.logger.info(f"Counter: {self._counter_value}")

        self._result_counter = CounterResult(final_value=self._counter_value)
        workflow.logger.info(f"Counter phase done - final value: {self._counter_value}")

    async def _run_password_cracker(self) -> None:
        """
        Phase 2 - Password Cracker
        Loops generate_pin → validate_pin until the target PIN is matched or the
        max-attempt ceiling is hit.  Supports:
          • override_pin signal  - inject a specific guess next iteration
          • stop signal          - abandon immediately
        Demonstrates: activity loop, interdependent activities, signal-driven
        override, queries for live attempt count.
        """
        workflow.logger.info("=== Phase 2: Password Cracker ===")
        self._crack_attempt = 0
        self._crack_cracked = False
        MAX_ATTEMPTS = 1000

        while self._crack_attempt < MAX_ATTEMPTS and not self._stopped:
            await self._honour_pause()
            if self._stopped:
                break

            self._crack_attempt += 1

            # Honour override PIN injected via signal
            if self._crack_override is not None:
                self._crack_current = self._crack_override
                self._crack_override = None
                workflow.logger.info(f"Using override PIN: {self._crack_current!r}")
            else:
                self._crack_current = await workflow.execute_activity(
                    generate_pin,
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        backoff_coefficient=2.0,
                        maximum_attempts=3,
                    ),
                )

            matched = await workflow.execute_activity(
                validate_pin,
                args=[self._crack_current, self._target_pin],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )

            if matched:
                self._crack_cracked = True
                workflow.logger.info(
                    f"PIN cracked: {self._crack_current!r} on attempt {self._crack_attempt}"
                )
                break

        self._result_cracker = CrackerResult(
            cracked=self._crack_cracked,
            attempts=self._crack_attempt,
            pin=self._crack_current if self._crack_cracked else None,
        )
        workflow.logger.info("Password cracker phase done")

    async def _run_file_processor(self) -> None:
        """
        Phase 3 - Parallel File Processor
        Accepts file IDs via the queue_file signal and launches each as an
        independent activity handle (non-blocking start_activity), achieving
        parallel execution.  Runs until the advance_phase signal is received,
        then awaits all outstanding handles before moving on.
        Demonstrates: parallel activities via start_activity handles, signal-fed
        dynamic work injection, query for in-flight task count.
        """
        workflow.logger.info("=== Phase 3: Parallel File Processor ===")
        self._file_handles = []
        self._files_processed = []
        self._advance_phase = False

        def _launch_queued() -> None:
            while self._file_queue:
                fid = self._file_queue.pop(0)
                handle = workflow.start_activity(
                    process_file,
                    fid,
                    start_to_close_timeout=timedelta(seconds=60),
                    heartbeat_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=2),
                        backoff_coefficient=2.0,
                        maximum_attempts=3,
                    ),
                )
                self._file_handles.append((fid, handle))
                workflow.logger.info(f"Launched activity for file {fid}")

        # Launch any files already queued before phase started
        _launch_queued()

        # Keep polling for new files until advance_phase / stop
        while not self._advance_phase and not self._stopped:
            await self._honour_pause()
            if self._stopped:
                break
            _launch_queued()
            await workflow.sleep(timedelta(seconds=1))

        # Await all in-flight activity handles
        for fid, handle in self._file_handles:
            try:
                result = await handle
                self._files_processed.append(result)
                workflow.logger.info(f"File {fid} complete: {result}")
            except Exception as exc:
                msg = f"File {fid} failed: {exc}"
                self._files_processed.append(msg)
                workflow.logger.warning(msg)

        self._result_file_processor = FileProcessorResult(
            processed=list(self._files_processed),
            total=len(self._files_processed),
        )
        workflow.logger.info("File processor phase done")

    async def _run_calculator_phase(self) -> None:
        """
        Phase 4 - Calculator
        Continuously generates two random operands and runs all four arithmetic
        operations until the advance_phase signal is received.
        Demonstrates: looped activity execution, advance_phase to exit, queries
        for live result stream plus on-demand update handler run_calculator.
        """
        workflow.logger.info("=== Phase 4: Calculator ===")
        self._calc_results = []
        self._advance_phase = False
        ops = ["add", "subtract", "multiply", "divide"]

        while not self._advance_phase and not self._stopped:
            await self._honour_pause()
            if self._stopped:
                break

            a = await workflow.execute_activity(
                generate_operand,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )
            b = await workflow.execute_activity(
                generate_operand,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                ),
            )

            for op in ops:
                result = await workflow.execute_activity(
                    calculate,
                    args=[a, b, op],
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        backoff_coefficient=2.0,
                        maximum_attempts=3,
                    ),
                )
                self._calc_results.append(result)
                workflow.logger.info(f"Calc: {result}")

            await workflow.sleep(timedelta(seconds=1))

        self._result_calculator = CalculatorResult(
            total_operations=len(self._calc_results),
            last_5=self._calc_results[-5:],
        )
        workflow.logger.info("Calculator phase done")

    async def _run_media_processor(self) -> None:
        """
        Phase 5 - Media Processor (Child Workflows)
        Spawns FileProcessingChildWorkflow and VideoProcessingChildWorkflow as
        child workflows and awaits them both concurrently with asyncio.gather.
        Demonstrates: child workflow execution, parallel child workflows, each
        child has its own isolated history and retry scope.
        """
        workflow.logger.info("=== Phase 5: Media Processor (Child Workflows) ===")
        self._media_results = {}

        wf_id = workflow.info().workflow_id

        file_handle = await workflow.start_child_workflow(
            FileProcessingChildWorkflow.run,
            id=f"{wf_id}-child-file",
            task_queue=TASK_QUEUE,
        )
        video_handle = await workflow.start_child_workflow(
            VideoProcessingChildWorkflow.run,
            id=f"{wf_id}-child-video",
            task_queue=TASK_QUEUE,
        )

        file_result, video_result = await asyncio.gather(file_handle, video_handle)

        self._result_media_processor = MediaProcessorResult(
            file_processing=file_result,
            video_processing=video_result,
        )
        self._media_results = {
            "file_processing": file_result,
            "video_processing": video_result,
        }
        workflow.logger.info(
            f"Media processor done - file={file_result!r}, video={video_result!r}"
        )

    async def _run_resilience_test(self) -> None:
        """
        Phase 6 - Resilience Test
        Executes random_fail_task which fails ~65 % of the time.  The
        exponential-back-off retry policy retries up to 10 times automatically,
        demonstrating Temporal's durable execution and retry mechanics.
        """
        workflow.logger.info("=== Phase 6: Resilience Test ===")

        self._resilience_result = await workflow.execute_activity(
            random_fail_task,
            start_to_close_timeout=timedelta(seconds=60),
            heartbeat_timeout=timedelta(seconds=15),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                backoff_coefficient=1.5,
                maximum_attempts=10,
            ),
        )

        self._result_resilience_test = ResilienceResult(result=self._resilience_result)
        workflow.logger.info(f"Resilience test done: {self._resilience_result}")

    # Helpers

    async def _honour_pause(self) -> None:
        """Block until the paused flag is cleared (or a stop is requested)."""
        if self._paused:
            workflow.logger.info("Workflow paused - waiting for resume...")
            await workflow.wait_condition(lambda: not self._paused or self._stopped)
            if not self._stopped:
                workflow.logger.info("Workflow resumed")

    def _build_result(self, status: str) -> ShowcaseResults:
        return ShowcaseResults(
            status=status,
            counter=self._result_counter,
            password_cracker=self._result_cracker,
            file_processor=self._result_file_processor,
            calculator=self._result_calculator,
            media_processor=self._result_media_processor,
            resilience_test=self._result_resilience_test,
        )
