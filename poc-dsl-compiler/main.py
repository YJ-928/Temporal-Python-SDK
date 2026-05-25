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
#   python main.py                        # default: examples/workflow_1_output.json
#   python main.py workflow.json          # resolved from input/ dir
#   python main.py /full/path/to/wf.json  # absolute path used directly

import json
import os
import sys

# Package root on path so sibling modules resolve without install
sys.path.insert(0, os.path.dirname(__file__))

from compiler import run_compiler, print_graph
from dsl_generator import generate_dsl, save_dsl


BASE = os.path.dirname(__file__)
DEFAULT_INPUT = os.path.join(BASE, "examples", "workflow_1_output.json")
DEFAULT_OUTPUT = os.path.join(BASE, "output", "generated_dsl.json")

def resolve_input_path(arg: str | None) -> str:
    """
    Resolve the input JSON path.

    - No arg:                 use DEFAULT_INPUT (examples/workflow_1_output.json)
    - Absolute path:          use as-is
    - Relative path that exists under cwd: use as-is (e.g. poc-dsl-compiler/examples/...)
    - Bare filename:          resolve from input/ directory
    """
    if arg is None:
        return DEFAULT_INPUT

    if os.path.isabs(arg):
        return arg

    # Relative path that resolves from the current working directory
    cwd_path = os.path.join(os.getcwd(), arg)
    if os.path.exists(cwd_path):
        return cwd_path

    # Bare filename look inside the input/ directory
    return os.path.join(BASE, "input", arg)

def main():
    input_path = resolve_input_path(sys.argv[1] if len(sys.argv) > 1 else None)
    output_path = DEFAULT_OUTPUT

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
    dsl = generate_dsl(traversal)
    save_dsl(dsl, output_path)

    print(f"=== DSL Output: {output_path} ===")
    print(json.dumps(dsl, indent=2))


if __name__ == "__main__":
    main()
