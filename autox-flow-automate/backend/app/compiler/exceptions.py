"""
Compiler validation exceptions.
"""

class WorkflowValidationError(ValueError):
    """Base class for all workflow validation errors."""


class GraphValidationError(WorkflowValidationError):
    """Raised for any graph topology/validity issues."""


class CycleDetectedError(GraphValidationError):
    """Raised when the graph contains cycles/loops."""


class MissingBranchError(GraphValidationError):
    """Raised when an IF node is missing true or false branch edges."""
