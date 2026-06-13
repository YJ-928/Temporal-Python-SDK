"""
Workflow domain API messages.
"""
from enum import Enum
from .api_msg import Message


class WorkflowAPIMsg(Enum):
    COMPILED = Message("WORKFLOW_COMPILED", "Workflow compiled and registered successfully.")
    NOT_FOUND = Message("WORKFLOW_NOT_FOUND", "Workflow '{}' not found.")
    COMPILE_FAILED = Message("WORKFLOW_COMPILE_FAILED", "Workflow compilation failed.")
    EXECUTION_STARTED = Message("WORKFLOW_EXECUTION_STARTED", "Workflow execution started.")
    EXECUTION_NOT_REGISTERED = Message("WORKFLOW_NOT_REGISTERED", "Workflow version is not registered. Please recompile.")
    EXECUTION_WARMING_UP = Message("WORKFLOW_WARMING_UP", "Workflow is warming up. Please retry in a moment.")
    RUNTIME_OFFLINE = Message("RUNTIME_OFFLINE", "Workflow runtime is offline.")
