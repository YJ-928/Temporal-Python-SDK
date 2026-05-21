"""
reactflow_to_temporal.py
Converts a React Flow graph JSON (nodes + edges) into a Temporal workflow DSL JSON.

Conversion rules
----------------
1. text-input node           -> captureInput  (set block)
2. agent-node (router)       -> parse<n> call + save<n> set,
                                immediately followed by routeByIntent switch block
3. Conditional edges         -> one switch case per edge + a default case
4. Each switch-target node   -> a named "do" block (runHotel, runRestaurant, ...)
5. Always appended           -> setDefaultMessage fallback do block
"""

import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_pascal(name: str) -> str:
    """'hotel' -> 'Hotel'"""
    return name.capitalize()


def make_call_step(step_name: str, agent_name: str,
                   query_ref: str = "${ $data.user_query }") -> dict:
    return {
        step_name: {
            "call": "activity",
            "with": {
                "name": "activity.execute_agent",
                "arguments": [query_ref, agent_name],
                "taskQueue": "activity_queue",
            },
        }
    }


def make_set_step(step_name: str, mapping: dict) -> dict:
    return {step_name: {"set": mapping}}


def make_do_block(block_name: str, steps: list) -> dict:
    return {block_name: {"do": steps}}


def camelkey_to_snake(key: str) -> str:
    """'userQuery' -> 'user_query'"""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()


# ---------------------------------------------------------------------------
# Core converter
# ---------------------------------------------------------------------------

def convert(flow: dict) -> dict:
    nodes: list = flow["nodes"]
    edges: list = flow["edges"]

    node_by_id = {n["id"]: n for n in nodes}

    input_nodes = [n for n in nodes if n["type"] == "text-input"]
    agent_nodes = [n for n in nodes if n["type"] == "agent-node"]

    conditional_edges = [e for e in edges if e.get("data", {}).get("condition")]

    # Router: agent node that emits conditional edges
    router_ids = {e["source"] for e in conditional_edges}
    # Switch targets: destinations of conditional edges
    switch_target_ids = {e["target"] for e in conditional_edges}

    # Pre-switch: all agent nodes that are NOT switch targets, sorted by y
    pre_switch_nodes = sorted(
        [n for n in agent_nodes if n["id"] not in switch_target_ids],
        key=lambda n: n["position"]["y"],
    )

    # Switch-target nodes sorted by y for deterministic output
    switch_target_nodes = sorted(
        [node_by_id[nid] for nid in switch_target_ids],
        key=lambda n: n["position"]["y"],
    )

    do_steps = []

    # 1. captureInput
    for inp in input_nodes:
        key = inp["data"]["key"]
        snake = camelkey_to_snake(key)
        do_steps.append(
            make_set_step("captureInput", {snake: "${ $input." + snake + " }"})
        )

    # 2+3. Pre-switch agent nodes: parse+save, then switch if router
    for node in pre_switch_nodes:
        name = node["data"]["name"]
        result_key = name + "Result"

        do_steps.append(make_call_step("parse" + to_pascal(name), name))
        do_steps.append(make_set_step("save" + to_pascal(name), {result_key: "${ $output }"}))

        if node["id"] in router_ids:
            outgoing = [e for e in conditional_edges if e["source"] == node["id"]]
            cases = []
            for edge in outgoing:
                target = node_by_id[edge["target"]]
                tname = target["data"]["name"]
                raw_cond = edge["data"]["condition"]
                dsl_cond = "${ $data." + result_key + "." + raw_cond + " }"
                run_label = "run" + to_pascal(tname)
                cases.append({tname: {"when": dsl_cond, "then": run_label}})
            cases.append({"default": {"then": "setDefaultMessage"}})
            do_steps.append({"routeByIntent": {"switch": cases}})

    # 4. Named do-blocks for switch targets
    for target_node in switch_target_nodes:
        name = target_node["data"]["name"]
        block_name = "run" + to_pascal(name)
        call_name = "run" + to_pascal(name) + "Activity"
        inner = [
            make_call_step(call_name, name),
            make_set_step("set" + to_pascal(name) + "Response", {"response": "${ $output.text }"}),
        ]
        do_steps.append(make_do_block(block_name, inner))

    # 5. Always append default fallback
    do_steps.append(
        make_do_block(
            "setDefaultMessage",
            [make_set_step("setDefault", {
                "response": "I'm not able to answer your query please try another"
            })],
        )
    )

    return {
        "document": {
            "dsl": "1.0.0",
            "namespace": "zigflow",
            "name": "agent-router",
            "version": "0.0.1",
        },
        "do": do_steps,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    input_path  = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("react-flow/output.json")
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("workflow/converted-workflow.json")

    with input_path.open() as f:
        flow = json.load(f)

    result = convert(flow)

    with output_path.open("w") as f:
        json.dump(result, f, indent=2)

    print("Converted '{}' -> '{}'".format(input_path, output_path))


if __name__ == "__main__":
    main()