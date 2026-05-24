import json
import random
from pathlib import Path


SUPPORTED_NODE_TYPES = [
    "INPUT",
    "ACTION",
    "OUTPUT",
]


def generate_input(node_id):

    return {
        "id": node_id,
        "type": "INPUT",
        "data": {
            "inputs": [
                {
                    "field": f"field_{node_id}",
                    "store_as": f"var_{node_id}",
                    "type": "string",
                }
            ]
        },
    }


def generate_action(node_id, previous_node):

    input_var = (
        previous_node.get("data", {}).get("inputs", [{}])[0].get("store_as", "input")
        if previous_node["type"] == "INPUT"
        else "result"
    )

    return {
        "id": node_id,
        "type": "ACTION",
        "data": {
            "operation": f"operation_{node_id}",
            "inputs": {"value": input_var},
            "output": f"result_{node_id}",
        },
    }


def generate_output(node_id):

    return {
        "id": node_id,
        "type": "OUTPUT",
        "data": {
            "outputs": [
                {
                    "field": f"result_{node_id}",
                    "type": "string",
                }
            ]
        },
    }


def generate_node(node_id, node_type, previous=None):

    if node_type == "INPUT":
        return generate_input(node_id)

    if node_type == "ACTION":
        return generate_action(node_id, previous)

    if node_type == "OUTPUT":
        return generate_output(node_id)

    raise Exception("Unsupported node")


def generate_workflow(
    total_nodes=10,
    branches=2,
):

    nodes = []
    edges = []

    nodes.append(
        {
            "id": "N1",
            "type": "START",
        }
    )

    current = 2

    root = "N1"

    branch_starts = []

    input_node = generate_input(f"N{current}")

    nodes.append(input_node)

    edges.append(
        {
            "id": "E1",
            "source": root,
            "target": f"N{current}",
        }
    )

    branch_starts.append(f"N{current}")

    current += 1
    edge_counter = 2

    remaining = total_nodes - 3

    branch_size = max(
        1,
        remaining // branches,
    )

    for branch in range(branches):
        previous = input_node

        parent = branch_starts[0]

        for _ in range(branch_size):
            if current >= total_nodes:
                break

            node_type = random.choice(SUPPORTED_NODE_TYPES)

            node = generate_node(
                f"N{current}",
                node_type,
                previous,
            )

            nodes.append(node)

            edges.append(
                {
                    "id": f"E{edge_counter}",
                    "source": parent,
                    "target": f"N{current}",
                }
            )

            edge_counter += 1

            parent = f"N{current}"

            previous = node

            current += 1

    end_node = f"N{current}"

    nodes.append(
        {
            "id": end_node,
            "type": "END",
        }
    )

    for node in nodes:
        if node["type"] == "OUTPUT":
            edges.append(
                {
                    "id": f"E{edge_counter}",
                    "source": node["id"],
                    "target": end_node,
                }
            )

            edge_counter += 1

    return {
        "nodes": nodes,
        "edges": edges,
    }


def generate_mermaid(workflow):

    lines = ["graph TD"]

    for node in workflow["nodes"]:
        lines.append(f"{node['id']}[{node['type']}]")

    for edge in workflow["edges"]:
        lines.append(f"{edge['source']} --> {edge['target']}")

    return "\n".join(lines)


def save_workflow(
    workflow,
    folder="generated",
):

    output = Path(folder)

    output.mkdir(exist_ok=True)

    json_path = output / "workflow.json"

    md_path = output / "workflow.md"

    with open(
        json_path,
        "w",
    ) as f:
        json.dump(
            workflow,
            f,
            indent=2,
        )

    with open(
        md_path,
        "w",
    ) as f:
        f.write(generate_mermaid(workflow))

    print(f"\nJSON → {json_path}")

    print(f"MERMAID → {md_path}")


if __name__ == "__main__":
    node_count = int(input("\nTotal Nodes: "))

    branch_count = int(input("Branches: "))

    workflow = generate_workflow(
        node_count,
        branch_count,
    )

    save_workflow(workflow)

    print("\nWorkflow Generated")
