"""
Demo POC — Shared Dataclasses
==============================
All typed input / output structures for signals, updates, queries, and
workflow results used across the Demo POC.

Best practice (docs/03, docs/04, docs/20):
  "Use dataclasses for all structured input/output instead of raw primitives
   or plain dicts — they give you type safety, IDE completion, and clean
   serialisation via Temporal's default DataConverter."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Signal Inputs 

@dataclass
class StartInput:
    """Payload for the start signal — carries the target PIN for Phase 2."""
    target_pin: str


# Update Inputs / Outputs 

@dataclass
class CalculatorInput:
    """Input for the run_calculator update handler."""
    a: int
    b: int
    op: str  # add | subtract | multiply | divide


@dataclass
class PinMatchInput:
    """Input for the test_pin_match update handler."""
    guess: str
    target: str


# Query Return Types

@dataclass
class WorkflowStatus:
    """Returned by get_status() query — high-level workflow lifecycle state."""
    phase: str
    started: bool
    paused: bool
    stopped: bool
    target_pin: str


@dataclass
class CounterProgress:
    counter_value: int
    stopped: bool


@dataclass
class CrackerProgress:
    attempt: int
    current_pin: str
    cracked: bool


@dataclass
class FileProcessorProgress:
    queued: list[int]
    in_flight: int
    completed: list[str]


@dataclass
class CalculatorProgress:
    total_ops: int
    last_5: list[str]


@dataclass
class MediaProgress:
    file_result: str
    video_result: str


@dataclass
class ResilienceProgress:
    result: str


@dataclass
class PhaseProgress:
    """
    Returned by get_phase_progress() query.
    Only the field matching the current phase will be populated; others are None.
    """
    phase: str
    counter: Optional[CounterProgress] = None
    cracker: Optional[CrackerProgress] = None
    file_processor: Optional[FileProcessorProgress] = None
    calculator: Optional[CalculatorProgress] = None
    media: Optional[MediaProgress] = None
    resilience: Optional[ResilienceProgress] = None


# Phase Result Types (accumulated across completion)

@dataclass
class CounterResult:
    final_value: int


@dataclass
class CrackerResult:
    cracked: bool
    attempts: int
    pin: Optional[str] = None


@dataclass
class FileProcessorResult:
    processed: list[str]
    total: int


@dataclass
class CalculatorResult:
    total_operations: int
    last_5: list[str] = field(default_factory=list)


@dataclass
class MediaProcessorResult:
    file_processing: str
    video_processing: str


@dataclass
class ResilienceResult:
    result: str


@dataclass
class ShowcaseResults:
    """
    Final output returned when the workflow ends (or when get_results() is queried).
    Each field corresponds to a phase; it is None if that phase has not completed yet.
    """
    status: str
    counter: Optional[CounterResult] = None
    password_cracker: Optional[CrackerResult] = None
    file_processor: Optional[FileProcessorResult] = None
    calculator: Optional[CalculatorResult] = None
    media_processor: Optional[MediaProcessorResult] = None
    resilience_test: Optional[ResilienceResult] = None
