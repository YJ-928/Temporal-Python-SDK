"""
Compiler package for workflow JSON → Zigflow DSL compilation.
"""
from .exceptions import (
    WorkflowValidationError,
    GraphValidationError,
    CycleDetectedError,
    MissingBranchError,
)
from .graph import (
    compile_workflow,
    generate_node_map,
    generate_adjacency_list,
    find_entrypoint,
    traverse_graph,
    resolve_task_name,
    validate_graph,
)
from .dsl_generator import (
    generate_dsl,
    register_builder,
    BUILDER_REGISTRY,
)
from .workflow_compiler import (
    compile_workflow_to_dsl,
    initialize_builders,
)


__all__ = [
    # Exceptions
    "WorkflowValidationError",
    "GraphValidationError",
    "CycleDetectedError",
    "MissingBranchError",
    # Phase A - Graph compilation
    "compile_workflow",
    "generate_node_map",
    "generate_adjacency_list",
    "find_entrypoint",
    "traverse_graph",
    "resolve_task_name",
    "validate_graph",
    # Phase B - DSL generation
    "generate_dsl",
    "register_builder",
    "BUILDER_REGISTRY",
    # Workflow compiler (main entry point)
    "compile_workflow_to_dsl",
    "initialize_builders",
]
