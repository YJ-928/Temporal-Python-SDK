"""
pipeline.py — Single integration layer between the demo UI and the compiler.

This is the ONLY module in demo/ that imports from the compiler packages.
All compiler functions are synchronous; callers should run them via
asyncio.run_in_executor to avoid blocking the FastAPI event loop.
"""

import json
import os
import subprocess
import tempfile

from compiler import run_compiler
from dsl_generator import generate_dsl
from workflow_generator import (
    DESCRIPTIONS,
    GENERATORS,
    generate_mermaid,
    shuffle_nodes,
)

# Re-export so app.py can import DESCRIPTIONS from demo.pipeline
__all__ = ["DESCRIPTIONS", "generate_workflow", "compile_workflow", "validate_dsl", "run_full_pipeline", "compile_custom"]


# ─── helpers ─────────────────────────────────────────────────────────────────

def _strip_mermaid_fence(raw: str) -> str:
    """Remove the ```mermaid ... ``` wrapper so Mermaid.js can render inline."""
    lines = raw.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


def _compute_metrics(workflow: dict, compiler_output: dict) -> dict:
    """Derive display metrics from the workflow and compiler output."""
    nodes = workflow["nodes"]
    edges = workflow["edges"]
    traversal = compiler_output["traversal"]

    node_types_seen = sorted({n["type"] for n in nodes if n["type"] not in ("START", "END")})

    # Derive a topology label from node types present
    type_set = {n["type"] for n in nodes}
    if "PARALLEL" in type_set:
        topology = "PARALLEL Fork"
    elif "IF" in type_set:
        topology = "IF Branching"
    elif any(n["type"] == "WAIT" and n.get("data", {}).get("mode") == "listen" for n in nodes):
        topology = "Signal Listen"
    elif "WAIT" in type_set:
        topology = "Wait / Timer"
    else:
        topology = "Linear"

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "traversal_steps": len(traversal),
        "node_types": node_types_seen,
        "topology_label": topology,
    }


def _build_adjacency_display(adjacency: dict, node_map: dict) -> list:
    """Serialise adjacency list into a JSON-friendly structure for the UI."""
    result = []
    for source_id, targets in adjacency.items():
        result.append({
            "source": source_id,
            "source_type": node_map.get(source_id, {}).get("type", "?"),
            "targets": [
                {
                    "id": t_id,
                    "type": node_map.get(t_id, {}).get("type", "?"),
                    "control": ctrl,
                }
                for t_id, ctrl in targets
            ],
        })
    return result


def _build_traversal_display(traversal: list) -> list:
    """Convert TraversalEntry list to a JSON-serialisable form for the UI.

    parallel_map and branch traversals are omitted to avoid deeply nested
    objects that would be hard to read in the UI.
    """
    result = []
    for i, entry in enumerate(traversal):
        display = {
            "step": i + 1,
            "node_id": entry["node_id"],
            "node_type": entry["node_type"],
            "is_terminal": entry.get("is_terminal", False),
            "successors": entry.get("successors", []),
        }
        if entry.get("incoming_edge_control"):
            display["incoming_edge_control"] = entry["incoming_edge_control"]
        if entry.get("branch_map"):
            display["branch_map"] = entry["branch_map"]
        if entry.get("reads_from_context"):
            display["reads_from_context"] = True
        if entry.get("parallel_map"):
            display["parallel_branches"] = list(entry["parallel_map"].keys())
        result.append(display)
    return result


# ─── core functions ───────────────────────────────────────────────────────────

def generate_workflow(level: int) -> dict:
    """Generate a random workflow for the given difficulty level.

    Returns a dict with keys:
        workflow_json   - raw workflow dict (nodes + edges)
        mermaid_raw     - Mermaid diagram string (fences stripped, ready for .mermaid div)
        level           - the requested level
        description     - human-readable level description
    """
    if level not in GENERATORS:
        raise ValueError(f"Invalid level {level!r}. Must be 1–14.")

    workflow = GENERATORS[level]()
    shuffle_nodes(workflow)
    mermaid_fenced = generate_mermaid(workflow)

    return {
        "workflow_json": workflow,
        "mermaid_raw": _strip_mermaid_fence(mermaid_fenced),
        "level": level,
        "description": DESCRIPTIONS[level],
    }


def compile_workflow(workflow: dict) -> dict:
    """Run Phase A + Phase B on a workflow dict.

    Returns a dict with keys:
        node_map           - {node_id: node} mapping
        adjacency_display  - serialised adjacency for UI display
        traversal_display  - serialised traversal entries for UI display
        dsl                - compiled Zigflow DSL dict
    """
    compiler_output = run_compiler(workflow)
    dsl = generate_dsl(compiler_output["traversal"])

    return {
        "node_map": compiler_output["node_map"],
        "adjacency_display": _build_adjacency_display(
            compiler_output["adjacency"], compiler_output["node_map"]
        ),
        "traversal_display": _build_traversal_display(compiler_output["traversal"]),
        "dsl": dsl,
        "_compiler_output": compiler_output,  # kept for metrics; not sent to client
    }


def validate_dsl(dsl: dict) -> dict:
    """Write DSL to a temp file, run `zigflow validate`, clean up.

    Returns a dict with keys:
        passed  - bool
        output  - CLI stdout/stderr (filtered of banner noise)
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="zigflow_demo_"
    )
    try:
        json.dump(dsl, tmp, indent=2)
        tmp.close()
        result = subprocess.run(
            ["zigflow", "validate", tmp.name],
            capture_output=True,
            text=True,
            timeout=15,
        )
        raw_output = (result.stdout + result.stderr).strip()
        # Filter out zigflow banner lines (contain "Zigflow" or are blank)
        filtered_lines = [
            line for line in raw_output.splitlines()
            if line.strip() and "zigflow" not in line.lower()[:20]
        ]
        return {
            "passed": result.returncode == 0,
            "output": "\n".join(filtered_lines) if filtered_lines else "(no output)",
        }
    except FileNotFoundError:
        return {"passed": False, "output": "zigflow CLI not found in PATH."}
    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "zigflow validate timed out."}
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def run_full_pipeline(level: int) -> dict:
    """Orchestrate generate → compile → validate for a difficulty level.

    Returns the combined result dict consumed by POST /api/pipeline.
    """
    gen_data = generate_workflow(level)
    workflow = gen_data["workflow_json"]

    compile_data = compile_workflow(workflow)
    compiler_output = compile_data.pop("_compiler_output")

    validation = validate_dsl(compile_data["dsl"])
    metrics = _compute_metrics(workflow, compiler_output)
    metrics["validation_passed"] = validation["passed"]

    return {
        "generator": {
            "level": gen_data["level"],
            "description": gen_data["description"],
            "mermaid_raw": gen_data["mermaid_raw"],
            "workflow_json": gen_data["workflow_json"],
        },
        "compiler": {
            "node_map": compile_data["node_map"],
            "adjacency_display": compile_data["adjacency_display"],
            "traversal_display": compile_data["traversal_display"],
        },
        "dsl": compile_data["dsl"],
        "validation": validation,
        "metrics": metrics,
    }


def compile_custom(workflow_json: dict) -> dict:
    """Compile a user-supplied workflow JSON dict (Paste JSON mode).

    Returns the same shape as run_full_pipeline() but without the generator key.
    """
    compile_data = compile_workflow(workflow_json)
    compiler_output = compile_data.pop("_compiler_output")

    validation = validate_dsl(compile_data["dsl"])
    metrics = _compute_metrics(workflow_json, compiler_output)
    metrics["validation_passed"] = validation["passed"]

    return {
        "compiler": {
            "node_map": compile_data["node_map"],
            "adjacency_display": compile_data["adjacency_display"],
            "traversal_display": compile_data["traversal_display"],
        },
        "dsl": compile_data["dsl"],
        "validation": validation,
        "metrics": metrics,
    }
