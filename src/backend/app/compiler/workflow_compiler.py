"""
Main compiler entry point.

Wires together graph validation, graph compilation, builder registration, and DSL generation.
"""
from pydantic import ValidationError
from .exceptions import WorkflowValidationError
from .graph import (
    compile_workflow,
    generate_node_map,
    generate_adjacency_list,
    validate_graph,
)
from .dsl_generator import generate_dsl, register_builder
from ..builders import BUILDERS
from ..schemas.workflow_sch import WorkflowDefinition
from ..config import compiler_settings


def initialize_builders() -> None:
    """
    Register all node builders with the DSL generator.
    """
    for node_type, builder_fn in BUILDERS.items():
        register_builder(node_type, builder_fn)


def validate_workflow_structure(workflow: dict) -> None:
    """
    Validate the incoming workflow dict against Pydantic schemas and graph validation rules.

    Args:
        workflow: dict with "nodes" and "edges" keys

    Raises:
        WorkflowValidationError: If schema validation fails
        GraphValidationError: If graph topology checks fail
    """
    # 1. Pydantic validation (Node-type specific rules)
    try:
        WorkflowDefinition(**workflow)
    except ValidationError as e:
        errors = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")
        raise WorkflowValidationError(f"Schema validation failed: {'; '.join(errors)}")

    # 2. Graph topology validation
    node_map = generate_node_map(workflow["nodes"])
    adjacency = generate_adjacency_list(workflow["edges"])
    validate_graph(workflow["nodes"], workflow["edges"], node_map, adjacency)


def compile_workflow_to_dsl(
    workflow: dict,
    dsl_version: str = compiler_settings.dsl_version,
    version: str = compiler_settings.workflow_version,
    workflow_type: str = compiler_settings.workflow_type,
    task_queue: str = compiler_settings.task_queue,
    description: str = "",
) -> dict:
    """
    Full compilation pipeline: Workflow JSON → Zigflow DSL.

    Args:
        workflow: dict with "nodes" and "edges" keys
        dsl_version: DSL spec version
        version: Workflow version
        workflow_type: Temporal workflow type
        task_queue: Temporal task queue name
        description: Workflow description

    Returns:
        Complete Zigflow DSL dict
    """
    # Initialize builders (idempotent)
    initialize_builders()

    # Phase 0: Validate workflow structure and topology
    validate_workflow_structure(workflow)

    # Phase A: Graph compilation and traversal
    compilation_result = compile_workflow(workflow)
    traversal = compilation_result["traversal"]

    # Phase B: DSL generation
    dsl = generate_dsl(
        traversal,
        dsl_version=dsl_version,
        version=version,
        workflow_type=workflow_type,
        task_queue=task_queue,
        description=description,
    )

    return dsl


__all__ = [
    "initialize_builders",
    "validate_workflow_structure",
    "compile_workflow_to_dsl",
]
