# main.py
#
# Single entry point for the DSL compiler pipeline.
#
# Flow:
#   1. Load workflow JSON from input/ dir (by filename) or by full path
#   2. run_compiler(workflow) → node_map, adjacency, graph, traversal
#   3. generate_dsl(traversal) → DSL dict
#   4. save_dsl(dsl, output_path)
#   5. Print: graph, traversal, DSL path + contents
#
# Usage:
#   python main.py                             # default: input/workflow_outputs/workflow_1_output.json
#   python main.py workflow_4_output           # resolved from input/workflow_outputs/ (.json added automatically)
#   python main.py workflow_4_output.json      # same, extension already present
#   python main.py /full/path/to/wf.json       # absolute path used directly

import json
import os
import sys

# Package root on path so sibling modules resolve without install
sys.path.insert(0, os.path.dirname(__file__))

from compiler import run_compiler, print_graph
from dsl_generator import generate_dsl, save_dsl


BASE = os.path.dirname(__file__)
DEFAULT_INPUT = os.path.join(BASE, "input", "workflow_outputs", "workflow_1_output.json")
INPUT_DIR = os.path.join(BASE, "input", "workflow_outputs")
OUTPUT_DIR = os.path.join(BASE, "output")

def resolve_output_path(input_path: str) -> str:
    """
    Derive the output filename from the input filename.

    Examples:
        workflow_1_output.json  →  output/workflow_1_dsl_schema.json
        my_flow.json            →  output/my_flow_dsl_schema.json
    """
    stem = os.path.splitext(os.path.basename(input_path))[0]  # e.g. "workflow_1_output"
    if stem.endswith("_output"):
        stem = stem[: -len("_output")]                        # e.g. "workflow_1"
    filename = f"{stem}_dsl_schema.json"                      # e.g. "workflow_1_dsl_schema.json"
    return os.path.join(OUTPUT_DIR, filename)

def resolve_input_path(arg: str | None) -> str:
    """
    Resolve the input JSON path.

    - No arg:              use DEFAULT_INPUT (input/workflow_outputs/workflow_1_output.json)
    - Absolute path:       used as-is; raises FileNotFoundError if missing
    - Relative path that exists under cwd: used as-is
    - Bare name (with or without .json): looked up in input/workflow_outputs/
    """
    if arg is None:
        return DEFAULT_INPUT

    if os.path.isabs(arg):
        if not os.path.exists(arg):
            raise FileNotFoundError(f"Input file not found: {arg}")
        return arg

    # Relative path that resolves from the current working directory
    cwd_path = os.path.join(os.getcwd(), arg)
    if os.path.exists(cwd_path):
        return cwd_path

    # Bare name — normalise extension then look in input/workflow_outputs/
    name = arg if arg.endswith(".json") else arg + ".json"
    candidate = os.path.join(INPUT_DIR, name)
    if os.path.exists(candidate):
        return candidate

    raise FileNotFoundError(
        f"Input file not found: '{arg}'\n"
        f"Expected location: {os.path.join(INPUT_DIR, name)}"
    )

def main():
    input_path = resolve_input_path(sys.argv[1] if len(sys.argv) > 1 else None)
    output_path = resolve_output_path(input_path)

    # Load JSON (UI workflow output)
    with open(input_path, encoding="utf-8") as f:
        workflow = json.load(f)

    print(f"Input:  {input_path}")
    print()

    # Compiler
    compiler_output = run_compiler(workflow)

    node_map  = compiler_output["node_map"]
    adjacency = compiler_output["adjacency"]
    graph     = compiler_output["graph"]
    traversal = compiler_output["traversal"]

    print("=== Node Map ===")
    print(node_map)
    print()

    print("=== Adjaceny List ===")
    print(adjacency)
    print()

    print("=== Graph ===")
    print_graph(graph)
    print()

    print("=== Traversal ===")
    for node in traversal:
        print(f"  {node['id']}  ({node['type']})")
    print()

    # DSL Generator
    dsl = generate_dsl(traversal, compiler_context=compiler_output["builder_context"])
    save_dsl(dsl, output_path)

    print(f"=== DSL Output: {output_path} ===")
    print(json.dumps(dsl, indent=2))


if __name__ == "__main__":
    main()
