"""
Compiler validation exceptions.
"""

class WorkflowValidationError(ValueError):
    """Base class for all workflow validation errors."""
    pass


class GraphValidationError(WorkflowValidationError):
    """Raised for any graph topology/validity issues."""
    pass


class CycleDetectedError(GraphValidationError):
    """Raised when the graph contains cycles/loops."""
    pass


class MissingBranchError(GraphValidationError):
    """Raised when an IF node is missing true or false branch edges."""
    pass
