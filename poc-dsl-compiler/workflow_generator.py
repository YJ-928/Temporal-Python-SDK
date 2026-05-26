import json
import random
import re
from pathlib import Path

# Paths

BASE_DIR = Path(__file__).parent
WORKFLOWS_DIR = BASE_DIR / "workflows"
OUTPUTS_DIR = BASE_DIR / "workflow_outputs"

# Vocabulary

INPUT_VOCAB = [
    {"field": "name", "store_as": "user_name", "label": "user name"},
    {"field": "email", "store_as": "user_email", "label": "email address"},
    {"field": "date_of_birth", "store_as": "dob", "label": "date of birth"},
    {"field": "product_id", "store_as": "product_id", "label": "product ID"},
    {"field": "order_id", "store_as": "order_id", "label": "order ID"},
    {"field": "location", "store_as": "user_location", "label": "location"},
    {"field": "phone_number", "store_as": "phone", "label": "phone number"},
    {"field": "user_id", "store_as": "user_id", "label": "user ID"},
    {"field": "city", "store_as": "city", "label": "city"},
    {"field": "country", "store_as": "country", "label": "country"},
]

ACTION_VOCAB = [
    {
        "operation": "greet",
        "label": "Generate personalized greeting",
        "output": "greeting",
    },
    {
        "operation": "validate_email",
        "label": "Validate email address",
        "output": "validation_result",
    },
    {
        "operation": "calculate_age",
        "label": "Calculate age from date of birth",
        "output": "age",
    },
    {
        "operation": "fetch_product",
        "label": "Fetch product details",
        "output": "product_details",
    },
    {
        "operation": "process_order",
        "label": "Process order",
        "output": "order_status",
    },
    {
        "operation": "send_notification",
        "label": "Send notification to user",
        "output": "notification_status",
    },
    {
        "operation": "lookup_location",
        "label": "Look up location data",
        "output": "location_data",
    },
    {
        "operation": "verify_phone",
        "label": "Verify phone number",
        "output": "phone_verified",
    },
    {
        "operation": "generate_report",
        "label": "Generate user activity report",
        "output": "report",
    },
    {
        "operation": "log_activity",
        "label": "Log user activity",
        "output": "log_id",
    },
    {
        "operation": "enrich_profile",
        "label": "Enrich user profile",
        "output": "enriched_profile",
    },
    {
        "operation": "geocode",
        "label": "Geocode location to coordinates",
        "output": "coordinates",
    },
    {
        "operation": "format_output",
        "label": "Format output for response",
        "output": "formatted_output",
    },
    {
        "operation": "send_email",
        "label": "Send email to user",
        "output": "email_status",
    },
]

WAIT_VOCAB = [
    {"seconds": 10,  "label": "10 seconds"},
    {"seconds": 30,  "label": "30 seconds"},
    {"seconds": 60,  "label": "60 seconds"},
    {"minutes": 1,   "label": "1 minute"},
    {"minutes": 2,   "label": "2 minutes"},
    {"minutes": 5,   "label": "5 minutes"},
    {"minutes": 10,  "label": "10 minutes"},
    {"minutes": 15,  "label": "15 minutes"},
    {"hours": 1,     "label": "1 hour"},
    {"hours": 2,     "label": "2 hours"},
]

# Reverse lookup: operation name to human-readable label
_OPERATION_LABELS = {a["operation"]: a["label"] for a in ACTION_VOCAB}

# Node Builders
def make_start(nid):
    return {"id": nid, "type": "START"}

def make_end(nid):
    return {"id": nid, "type": "END"}

def make_input(nid, fields):
    """fields: list of INPUT_VOCAB entries."""
    return {
        "id": nid,
        "type": "INPUT",
        "data": {
            "inputs": [
                {"field": f["field"], "store_as": f["store_as"], "type": "string"}
                for f in fields
            ]
        },
    }

def make_action(nid, operation, input_var, output_var):
    """input_var: name of the runtime variable passed in."""
    return {
        "id": nid,
        "type": "ACTION",
        "data": {
            "operation": operation,
            "inputs": {"value": input_var},
            "output": output_var,
        },
    }

def make_output(nid, fields):
    """fields: list of {field, type} dicts."""
    return {
        "id": nid,
        "type": "OUTPUT",
        "data": {
            "outputs": [
                {"field": f["field"], "type": f.get("type", "string")}
                for f in fields
            ]
        },
    }

def make_wait(nid, duration):
    """duration: one entry from WAIT_VOCAB (dict with a single time-unit key)."""
    unit, value = next((k, v) for k, v in duration.items() if k != "label")
    return {
        "id": nid,
        "type": "WAIT",
        "data": {
            "duration": {unit: value},
        },
    }

# Edge Builder
def make_edge(eid, src, tgt):
    return {"id": eid, "source": src, "target": tgt}

# Utilities
def get_next_index():
    """Return the next incremental workflow index based on existing markdown files."""
    if not WORKFLOWS_DIR.exists():
        return 1

    indices = []
    for f in WORKFLOWS_DIR.glob("workflow_*.md"):
        m = re.match(r"workflow_(\d+)\.md", f.name)
        if m:
            indices.append(int(m.group(1)))

    return max(indices) + 1 if indices else 1

def shuffle_nodes(workflow):
    """Shuffle the nodes array in-place. Edges are untouched (ID-based, not position-based)."""
    random.shuffle(workflow["nodes"])

# Mermaid Generation
def _node_label(node):
    t = node["type"]
    if t == "START":
        return "Start"
    if t == "END":
        return "End"
    if t == "INPUT":
        fields = [inp["field"].replace("_", " ") for inp in node["data"]["inputs"]]
        if len(fields) == 1:
            return f"Input: {fields[0]}"
        return "Input: " + " and ".join(fields)
    if t == "ACTION":
        op = node["data"]["operation"]
        return _OPERATION_LABELS.get(op, op.replace("_", " ").title())
    if t == "OUTPUT":
        fields = [out["field"].replace("_", " ") for out in node["data"]["outputs"]]
        if len(fields) == 1:
            return f"Output: {fields[0]}"
        return "Output: " + " and ".join(fields)
    if t == "WAIT":
        d = node["data"]["duration"]
        if "hours" in d:
            unit, n = "hour", d["hours"]
            return f"Wait: {n} {unit}{'s' if n != 1 else ''}"
        if "minutes" in d:
            unit, n = "minute", d["minutes"]
            return f"Wait: {n} {unit}{'s' if n != 1 else ''}"
        return f"Wait: {d['seconds']} seconds"
    return t

def _edge_label(src_node, tgt_node):
    st = src_node["type"]
    tt = tgt_node["type"]

    if st in ("START", "END", "OUTPUT"):
        return ""

    if st == "INPUT":
        if tt == "ACTION":
            # Show only the variable(s) the target ACTION actually uses
            used_vars = list(tgt_node["data"]["inputs"].values())
            return "{" + ", ".join(used_vars) + "}"
        return ""

    if st == "ACTION":
        return "{" + src_node["data"]["output"] + "}"

    return ""

def generate_mermaid(workflow):
    """Generate a fenced Mermaid diagram with semantic node labels."""
    node_map = {n["id"]: n for n in workflow["nodes"]}

    # Assign letters A, B, C... by sorted node ID (N1, N2, N3...)
    sorted_ids = sorted(node_map.keys(), key=lambda x: int(x[1:]))
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    letter_map = {nid: letters[i] for i, nid in enumerate(sorted_ids)}

    lines = ["```mermaid", "graph TD"]

    for edge in workflow["edges"]:
        src = edge["source"]
        tgt = edge["target"]
        src_l = letter_map[src]
        tgt_l = letter_map[tgt]
        src_label = _node_label(node_map[src])
        tgt_label = _node_label(node_map[tgt])
        label = _edge_label(node_map[src], node_map[tgt])

        if label:
            lines.append(f"    {src_l}[{src_label}] -- {label} --> {tgt_l}[{tgt_label}]")
        else:
            lines.append(f"    {src_l}[{src_label}] --> {tgt_l}[{tgt_label}]")

    lines.append("```")
    return "\n".join(lines)

# Level Generators
def generate_level_1():
    """
    Level 1 — Linear
    START to INPUT to ACTION to OUTPUT to END
    5 nodes, 4 edges
    """
    inp = random.choice(INPUT_VOCAB)
    act = random.choice(ACTION_VOCAB)

    nodes = [
        make_start("N1"),
        make_input("N2", [inp]),
        make_action("N3", act["operation"], inp["store_as"], act["output"]),
        make_output("N4", [{"field": act["output"], "type": "string"}]),
        make_end("N5"),
    ]

    edges = [
        make_edge("E1", "N1", "N2"),
        make_edge("E2", "N2", "N3"),
        make_edge("E3", "N3", "N4"),
        make_edge("E4", "N4", "N5"),
    ]

    return {"nodes": nodes, "edges": edges}

def generate_level_2():
    """
    Level 2 — 2 branches from shared INPUT, merge at END
    START to INPUT(2 fields) to ACTION to OUTPUT to END
                            to ACTION to OUTPUT ↗
    7 nodes, 7 edges
    """
    inputs = random.sample(INPUT_VOCAB, 2)
    actions = random.sample(ACTION_VOCAB, 2)

    nodes = [
        make_start("N1"),
        make_input("N2", inputs),
        make_action("N3", actions[0]["operation"], inputs[0]["store_as"], actions[0]["output"]),
        make_action("N4", actions[1]["operation"], inputs[1]["store_as"], actions[1]["output"]),
        make_output("N5", [{"field": actions[0]["output"], "type": "string"}]),
        make_output("N6", [{"field": actions[1]["output"], "type": "string"}]),
        make_end("N7"),
    ]

    edges = [
        make_edge("E1", "N1", "N2"),
        make_edge("E2", "N2", "N3"),
        make_edge("E3", "N2", "N4"),
        make_edge("E4", "N3", "N5"),
        make_edge("E5", "N4", "N6"),
        make_edge("E6", "N5", "N7"),
        make_edge("E7", "N6", "N7"),
    ]

    return {"nodes": nodes, "edges": edges}

def generate_level_3():
    """
    Level 3 — 3 branches from shared INPUT, merge at END
    START to INPUT(3 fields) to ACTION to OUTPUT to END
                            to ACTION to OUTPUT ↗
                            to ACTION to OUTPUT ↗
    9 nodes, 10 edges
    """
    inputs = random.sample(INPUT_VOCAB, 3)
    actions = random.sample(ACTION_VOCAB, 3)

    nodes = [
        make_start("N1"),
        make_input("N2", inputs),
        make_action("N3", actions[0]["operation"], inputs[0]["store_as"], actions[0]["output"]),
        make_output("N4", [{"field": actions[0]["output"], "type": "string"}]),
        make_action("N5", actions[1]["operation"], inputs[1]["store_as"], actions[1]["output"]),
        make_output("N6", [{"field": actions[1]["output"], "type": "string"}]),
        make_action("N7", actions[2]["operation"], inputs[2]["store_as"], actions[2]["output"]),
        make_output("N8", [{"field": actions[2]["output"], "type": "string"}]),
        make_end("N9"),
    ]

    edges = [
        make_edge("E1", "N1", "N2"),
        make_edge("E2", "N2", "N3"),
        make_edge("E3", "N3", "N4"),
        make_edge("E4", "N4", "N9"),
        make_edge("E5", "N2", "N5"),
        make_edge("E6", "N5", "N6"),
        make_edge("E7", "N6", "N9"),
        make_edge("E8", "N2", "N7"),
        make_edge("E9", "N7", "N8"),
        make_edge("E10", "N8", "N9"),
    ]

    return {"nodes": nodes, "edges": edges}

def generate_level_4():
    """
    Level 4 — 2 deep branches: each branch chains ACTION to ACTION to OUTPUT
    START to INPUT(2 fields) to ACTION to ACTION to OUTPUT to END
                            to ACTION to ACTION to OUTPUT ↗
    9 nodes, 9 edges
    """
    inputs = random.sample(INPUT_VOCAB, 2)
    actions = random.sample(ACTION_VOCAB, 4)
    a1, a2, a3, a4 = actions

    nodes = [
        make_start("N1"),
        make_input("N2", inputs),
        # Branch 1: a1 feeds a2
        make_action("N3", a1["operation"], inputs[0]["store_as"], a1["output"]),
        make_action("N4", a2["operation"], a1["output"], a2["output"]),
        make_output("N5", [{"field": a2["output"], "type": "string"}]),
        # Branch 2: a3 feeds a4
        make_action("N6", a3["operation"], inputs[1]["store_as"], a3["output"]),
        make_action("N7", a4["operation"], a3["output"], a4["output"]),
        make_output("N8", [{"field": a4["output"], "type": "string"}]),
        make_end("N9"),
    ]

    edges = [
        make_edge("E1", "N1", "N2"),
        # Branch 1
        make_edge("E2", "N2", "N3"),
        make_edge("E3", "N3", "N4"),
        make_edge("E4", "N4", "N5"),
        make_edge("E5", "N5", "N9"),
        # Branch 2
        make_edge("E6", "N2", "N6"),
        make_edge("E7", "N6", "N7"),
        make_edge("E8", "N7", "N8"),
        make_edge("E9", "N8", "N9"),
    ]

    return {"nodes": nodes, "edges": edges}

def generate_level_5():
    """
    Level 5 — Mixed depth: branch 1 is shallow, branch 2 has its own INPUT and a 3-action chain
    START to INPUT to ACTION to OUTPUT to END
          to INPUT to ACTION to ACTION to ACTION to OUTPUT ↗
    10 nodes, 10 edges
    """
    # Branch 1: single INPUT to single ACTION to OUTPUT
    inp_b1 = random.choice(INPUT_VOCAB)
    act_b1 = random.choice(ACTION_VOCAB)

    # Branch 2: separate INPUT to 3-action chain to OUTPUT
    remaining_inputs = [i for i in INPUT_VOCAB if i["field"] != inp_b1["field"]]
    inp_b2 = random.choice(remaining_inputs)

    remaining_actions = [a for a in ACTION_VOCAB if a["operation"] != act_b1["operation"]]
    acts_b2 = random.sample(remaining_actions, 3)
    a1, a2, a3 = acts_b2

    nodes = [
        make_start("N1"),
        # Branch 1
        make_input("N2", [inp_b1]),
        make_action("N3", act_b1["operation"], inp_b1["store_as"], act_b1["output"]),
        make_output("N4", [{"field": act_b1["output"], "type": "string"}]),
        # Branch 2 (its own INPUT)
        make_input("N5", [inp_b2]),
        make_action("N6", a1["operation"], inp_b2["store_as"], a1["output"]),
        make_action("N7", a2["operation"], a1["output"], a2["output"]),
        make_action("N8", a3["operation"], a2["output"], a3["output"]),
        make_output("N9", [{"field": a3["output"], "type": "string"}]),
        make_end("N10"),
    ]

    edges = [
        make_edge("E1", "N1", "N2"),
        make_edge("E2", "N2", "N3"),
        make_edge("E3", "N3", "N4"),
        make_edge("E4", "N4", "N10"),
        make_edge("E5", "N1", "N5"),
        make_edge("E6", "N5", "N6"),
        make_edge("E7", "N6", "N7"),
        make_edge("E8", "N7", "N8"),
        make_edge("E9", "N8", "N9"),
        make_edge("E10", "N9", "N10"),
    ]

    return {"nodes": nodes, "edges": edges}


def generate_level_6():
    """
    Level 6 — Linear with WAIT: ACTION output pauses before reaching OUTPUT
    START to INPUT to ACTION to WAIT to OUTPUT to END
    6 nodes, 5 edges
    """
    inp = random.choice(INPUT_VOCAB)
    act = random.choice(ACTION_VOCAB)
    wait = random.choice(WAIT_VOCAB)

    nodes = [
        make_start("N1"),
        make_input("N2", [inp]),
        make_action("N3", act["operation"], inp["store_as"], act["output"]),
        make_wait("N4", wait),
        make_output("N5", [{"field": act["output"], "type": "string"}]),
        make_end("N6"),
    ]

    edges = [
        make_edge("E1", "N1", "N2"),
        make_edge("E2", "N2", "N3"),
        make_edge("E3", "N3", "N4"),
        make_edge("E4", "N4", "N5"),
        make_edge("E5", "N5", "N6"),
    ]

    return {"nodes": nodes, "edges": edges}


def generate_level_7():
    """
    Level 7 — Two branches with WAITs; branch 1 has an extra ACTION after the WAIT
    START to INPUT(2 fields) to ACTION to WAIT to ACTION to OUTPUT to END
                            to ACTION to WAIT to OUTPUT ↗
    10 nodes, 10 edges
    """
    inputs = random.sample(INPUT_VOCAB, 2)
    actions = random.sample(ACTION_VOCAB, 4)
    a1, a2, a3, a4 = actions
    wait_b1 = random.choice(WAIT_VOCAB)
    wait_b2 = random.choice(WAIT_VOCAB)

    nodes = [
        make_start("N1"),
        make_input("N2", inputs),
        # Branch 1: ACTION → WAIT → ACTION → OUTPUT
        make_action("N3", a1["operation"], inputs[0]["store_as"], a1["output"]),
        make_wait("N4", wait_b1),
        make_action("N5", a2["operation"], a1["output"], a2["output"]),
        make_output("N6", [{"field": a2["output"], "type": "string"}]),
        # Branch 2: ACTION → WAIT → OUTPUT
        make_action("N7", a3["operation"], inputs[1]["store_as"], a3["output"]),
        make_wait("N8", wait_b2),
        make_output("N9", [{"field": a3["output"], "type": "string"}]),
        make_end("N10"),
    ]

    edges = [
        make_edge("E1", "N1", "N2"),
        # Branch 1
        make_edge("E2", "N2", "N3"),
        make_edge("E3", "N3", "N4"),
        make_edge("E4", "N4", "N5"),
        make_edge("E5", "N5", "N6"),
        make_edge("E6", "N6", "N10"),
        # Branch 2
        make_edge("E7", "N2", "N7"),
        make_edge("E8", "N7", "N8"),
        make_edge("E9", "N8", "N9"),
        make_edge("E10", "N9", "N10"),
    ]

    return {"nodes": nodes, "edges": edges}


# Save
def save_workflow(workflow, mermaid_str, index):
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    md_path = WORKFLOWS_DIR / f"workflow_{index}.md"
    json_path = OUTPUTS_DIR / f"workflow_{index}_output.json"

    with open(md_path, "w") as f:
        f.write(mermaid_str)

    with open(json_path, "w") as f:
        json.dump(workflow, f, indent=2)

    print(f"\nMarkdown to {md_path}")
    print(f"JSON     to {json_path}")

# Entry Point
GENERATORS = {
    1: generate_level_1,
    2: generate_level_2,
    3: generate_level_3,
    4: generate_level_4,
    5: generate_level_5,
    6: generate_level_6,
    7: generate_level_7,
}

DESCRIPTIONS = {
    1: "Linear   — START to INPUT to ACTION to OUTPUT to END",
    2: "Branches — 2 parallel branches from shared INPUT",
    3: "Branches — 3 parallel branches from shared INPUT",
    4: "Deep     — 2 branches with chained ACTIONs (INPUT to ACTION to ACTION to OUTPUT)",
    5: "Mixed    — 2 branches of different depths, branch 2 has its own INPUT",
    6: "Wait     — Linear with a WAIT (duration pause) between ACTION and OUTPUT",
    7: "Wait+    — 2 branches with WAITs; branch 1 has an extra ACTION after the WAIT",
}

if __name__ == "__main__":
    print("\nDifficulty Levels:")
    for k, v in DESCRIPTIONS.items():
        print(f"  {k}  {v}")

    level = int(input("\nDifficulty Level (1-7): "))

    if level not in GENERATORS:
        print("Invalid level. Choose 1-7.")
        raise SystemExit(1)

    workflow = GENERATORS[level]()
    shuffle_nodes(workflow)

    index = get_next_index()
    mermaid = generate_mermaid(workflow)
    save_workflow(workflow, mermaid, index)

    print(f"\nWorkflow {index} (Level {level} — {DESCRIPTIONS[level]}) generated.")
