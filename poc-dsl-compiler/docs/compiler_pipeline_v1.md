# 04 — Compiler Pipeline V1

## Overview

The compiler transforms a Graph JSON document into a Zigflow DSL YAML document through three sequential stages.

```
Input Graph JSON
       │
       ▼
┌─────────────────┐
│   1. Graph      │  Parse + index the raw JSON into an in-memory graph
│   (Parser)      │
└────────┬────────┘
         │  GraphModel
         ▼
┌─────────────────┐
│   2. Validator  │  Enforce structural constraints
│                 │  Reject invalid graphs before any DSL generation
└────────┬────────┘
         │  validated GraphModel
         ▼
┌─────────────────┐
│   3. DSL Builder│  Walk the graph, dispatch each node to its builder
│                 │  Emit Zigflow DSL dict, serialize to YAML
└────────┬────────┘
         │
         ▼
 Zigflow DSL YAML string
```

No intermediate representation. The DSL Builder walks the graph directly and emits DSL. An IR is a future concern once a second output target exists.

---

## Stage 1: Graph (Parser)

### Responsibility

Parse the raw JSON into a structured in-memory representation. Build adjacency indexes for fast traversal.

### Input

Raw Python `dict` (from `json.load()`).

### Output

A `GraphModel` object containing:
- `nodes: dict[str, Node]` — keyed by node ID
- `edges: list[Edge]`
- `adjacency: dict[str, list[str]]` — outgoing edges: `{ node_id → [target_id, ...] }`
- `handle_map: dict[tuple[str, str], str]` — maps `(source_id, target_id)` to `sourceHandle` value; used by IF to bind cases to targets without positional coupling
- `in_degree: dict[str, int]` — count of incoming edges per node
- `metadata: WorkflowMetadata` — contains `name` and `description` only

### Key operations

- Deserialise each entry in `nodes[]` into a typed `Node` object.
- Deserialise each entry in `edges[]` into an `Edge` object.
- Verify all `source` and `target` IDs in edges exist in `nodes`. Raise a `ParseError` if not.
- Build `adjacency` and `in_degree` maps from the edge list.
- Build `handle_map` from edges that carry a `sourceHandle` field. For PARALLEL, edge order still determines branch index.

### What it does NOT do

- No validation of constraints (tree shape, cycles, reachability). That is Stage 2.
- No transformation of node data. Raw `data` dicts are preserved as-is.

---

## Stage 2: Validator

### Responsibility

Enforce all graph constraints before any code generation begins. Fail fast with descriptive errors.

### Input

`GraphModel` from Stage 1.

### Output

The same `GraphModel` (unchanged), or a raised `ValidationError` listing all violations found.

### Checks (in order)

1. **Exactly one START node**
   - Count nodes with `type == "START"`. Must be exactly 1.

2. **Exactly one END node**
   - Count nodes with `type == "END"`. Must be exactly 1.

3. **START has no incoming edges**
   - `in_degree["start-node-id"]` must be 0.

4. **END has no outgoing edges**
   - `len(adjacency["end-node-id"])` must be 0.

5. **All edge references are valid**
   - Already done in Stage 1 (ParseError), but re-confirmed here.

6. **Max one parent per node (tree constraint)**
   - For every node except START: `in_degree[node_id] <= 1`.
   - Any node with `in_degree > 1` violates the tree constraint.

7. **No cycles (DAG check)**
   - Run DFS from START with a three-colour marking (`white` = unvisited, `grey` = in-progress, `black` = done).
   - A back-edge to a `grey` node indicates a cycle.

8. **Every node is reachable from START**
   - After DFS, any node remaining `white` is unreachable.

9. **IF nodes have sufficient outgoing edges**
   - `len(adjacency[if_node_id]) >= len(data.cases)`.
   - If `"default": true`, must have at least `len(cases) + 1` outgoing edges.
   - Every `case.id` in `data.cases` must match exactly one `sourceHandle` value on an outgoing edge. Missing or duplicate handle matches are a validation error.

10. **PARALLEL nodes have at least 2 outgoing edges**
    - `len(adjacency[parallel_node_id]) >= 2`.

11. **Task names are unique**
    - Collect resolved task names (from `data.name` or `id`) for all non-START, non-END nodes.
    - Names must be globally unique within the workflow.

### Error reporting

The validator collects all errors before raising. The raised `ValidationError` carries a list of all violations so the user sees every problem at once, not just the first.

---

## Stage 3: DSL Builder

### Responsibility

Walk the validated graph and emit Zigflow DSL dicts directly. No intermediate representation.

### Entry point

```python
compile(graph_model) -> str
    walk(start_node, graph_model) -> list[dict]
        node_registry[node.type](node, graph_model) -> dict
    yaml.dump({"document": ..., "do": task_list})
```

### Input

Validated `GraphModel`.

### Output

YAML string.

### Walk algorithm

1. Start at the START node.
2. Perform a **depth-first pre-order walk** following `adjacency`.
3. For each node:
   - If `START` or `END`: skip, continue to child.
   - Otherwise: look up `node_registry[node.type]` and call the builder function.
   - Append the returned dict to the `do` list.
4. For **IF** nodes: the builder resolves each `case.id` against `handle_map` to find the target node's task name. No positional dependency on edge order.
5. For **PARALLEL** nodes: the builder recursively calls `walk()` on each child subtree and wraps each result in a `branch` block.
6. For all other nodes (ACTION, VARIABLE, WORKFLOW, WAIT): builder returns a single task dict.

### Node registry (dispatch table)

```python
node_registry = {
    "ACTION":   build_action,
    "VARIABLE": build_variable,
    "WORKFLOW": build_workflow,
    "IF":       build_if,
    "PARALLEL": build_parallel,
    "WAIT":     build_wait,
}
```

Adding a new node type = add one entry to this dict and one builder function in `builders.py`. No other files change.

### Document assembly

```python
document = {
    "document": {
        "dsl": "1.0.0",
        "name": metadata.name,
        "version": "1.0.0",
    },
    "do": task_list
}
yaml.dump(document, default_flow_style=False, sort_keys=False)
```

`taskQueue` and `workflowType` are **not** emitted by the compiler. They are runtime concerns injected by the deployment layer.

`sort_keys=False` is required — Zigflow DSL is order-sensitive.

---

## Error Handling Strategy

| Stage | Error type | When raised |
|---|---|---|
| Graph (Parser) | `ParseError` | Missing/invalid edge references, malformed JSON structure |
| Validator | `ValidationError` | Any graph constraint violation (list of all violations) |
| DSL Builder | `BuildError` | Unknown node subtype, missing required `data` field, unmatched IF case handle |

All errors carry the violating `node_id` and a human-readable message. All validation errors are collected before raising — the caller sees every problem at once.

---

## Data Flow Summary

```
Graph JSON
    │
    │  json.load()
    ▼
raw dict
    │
    │  parse(raw_dict) → GraphModel
    ▼
GraphModel
  .nodes: { id → Node }
  .edges: [ Edge ]
  .adjacency: { id → [id] }
  .handle_map: { (src_id, tgt_id) → sourceHandle }
  .in_degree: { id → int }
  .metadata: WorkflowMetadata { name, description }
    │
    │  validate(graph_model)  →  None | raises ValidationError
    ▼
GraphModel (validated, unchanged)
    │
    │  compile(graph_model)
    │    walk(start_node) → list[dict]
    │      node_registry[node.type](node, graph_model) → dict
    │    yaml.dump({"document": ..., "do": task_list})
    ▼
YAML string
```

# Compiler Pipeline (Frozen — V1)

> **Status:** Frozen. Changes to function signatures must be reflected here.
> **Last updated:** May 2026
> **Implementation:** `poc-dsl-compiler/examples/workflow_compiler.py`

---

## Overview

The V1 compiler pipeline is a sequence of seven pure functions. Each function has a single, clearly defined responsibility. There is no shared mutable state. Every `compile()` call is independent and side-effect-free (except for debug `print()` calls in the current implementation).

```
compile(workflow)
  ├─ generate_node_map(workflow)
  ├─ generate_adjaceny_list(workflow)          ← note: typo in source, matches implementation
  ├─ find_entrypoint(node_map)
  ├─ generate_graph_structure(starting_point, node_map, adjaceny)
  ├─ print_graph(graph)                        ← debug only
  ├─ traverse_graph(graph)
  └─ [DSL Builder — not yet implemented]
```

---

## Stage 1 — `generate_node_map`

**Signature:**
```python
def generate_node_map(workflow: dict) -> dict
```

**Input:** The full workflow JSON dict (`{nodes: [...], edges: [...]}`)

**Output:** `dict[node_id → node]` — a flat index mapping each node's `id` to its full node object

**Responsibility:** Convert the raw `nodes` array into a lookup table so any subsequent stage can retrieve a node by ID in O(1) without re-scanning the array.

**Implementation pattern:**
```python
node_map = {}
for node in workflow["nodes"]:
    node_map[node["id"]] = node
return node_map
```

**Invariant:** Every node ID in the array must be unique. The compiler does not validate this in V1.

---

## Stage 2 — `generate_adjaceny_list`

> **Note:** The function name has a typo (`adjaceny` instead of `adjacency`). This matches the source file exactly. Do not rename without updating all call sites.

**Signature:**
```python
def generate_adjaceny_list(workflow: dict) -> dict
```

**Input:** The full workflow JSON dict

**Output:** `dict[source_id → list[target_id]]` — for each source node, the ordered list of node IDs it connects to

**Responsibility:** Convert the raw `edges` array into a neighbour lookup, enabling graph traversal without rescanning all edges for each step.

**Implementation pattern:**
```python
adjacency = {}
for edge in workflow["edges"]:
    source = edge["source"]
    target = edge["target"]
    if source not in adjacency:
        adjacency[source] = []
    adjacency[source].append(target)
return adjacency
```

**Notes:**
- Nodes with no outgoing edges do not appear as keys (use `adjacency.get(node_id, [])` to handle safely).
- Edge order within a source's list follows JSON array order. For branching nodes, this determines the DFS branch visit order.

---

## Stage 3 — `find_entrypoint`

**Signature:**
```python
def find_entrypoint(node_map: dict) -> str
```

**Input:** The `node_map` from Stage 1

**Output:** The `id` string of the `START` node, or `"Entrypoint not found"` if none exists

**Responsibility:** Locate the single `START` node to anchor all graph traversal.

**Implementation pattern:**
```python
for node_id, node in node_map.items():
    if node["type"] == "START":
        return node_id
return "Entrypoint not found"
```

**V1 limitation:** Returns a string sentinel on failure rather than raising an exception. This is intentional for the POC phase.

---

## Stage 4 — `generate_graph_structure`

**Signature:**
```python
def generate_graph_structure(entrypoint, node_map, adjacency, graph=None) -> dict
```

**Input:**
- `entrypoint` — node ID of the `START` node (from Stage 3)
- `node_map` — ID → node index (from Stage 1)
- `adjacency` — source → [target] map (from Stage 2)
- `graph` — memoization dict (internal use only; callers pass `None` or omit)

**Output:** The entry node's graph structure dict: `{"node": <node>, "children": [<same structure>, ...]}`

**Responsibility:** Build a recursive DAG representation. Shared nodes (nodes reachable from multiple parents) are memoized — they appear once in the structure and are referenced by pointer from all parents. This is the key mechanism that prevents shared nodes from being duplicated in the traversal.

**Implementation pattern:**
```python
if graph is None:
    graph = {}

if entrypoint in graph:
    return graph[entrypoint]             # return memoized reference

graph[entrypoint] = {"node": node_map[entrypoint], "children": []}

for child in adjacency.get(entrypoint, []):
    graph[entrypoint]["children"].append(
        generate_graph_structure(child, node_map, adjacency, graph)
    )

return graph[entrypoint]
```

**Critical constraint:** `graph` is the shared memo dict across the entire recursive call tree. When a node is encountered a second time (`entrypoint in graph`), the already-built subtree is returned directly rather than rebuilding it. This is how shared nodes in a DAG are handled without duplication.

---

## Stage 5 — `print_graph` (Debug Only)

**Signature:**
```python
def print_graph(graph, level=0, visited=None) -> None
```

**Input:**
- `graph` — the entry node's graph structure (from Stage 4)
- `level` — current indentation depth (internal recursion)
- `visited` — set of already-printed node IDs (internal recursion)

**Output:** None (prints to stdout only)

**Responsibility:** Visualise the graph structure as an indented DFS preorder tree. Already-visited shared nodes are printed with `[REF]` suffix instead of recursing into their children again.

**This function is for debugging only.** It is not part of the compiler output pipeline. The `[REF]` marker in output indicates a shared node being referenced from a second parent.

**Example output (branching workflow):**
```
START
  INPUT
    ACTION
      OUTPUT [REF]
    ACTION
      OUTPUT [REF]
  END [REF]
```

---

## Stage 6 — `traverse_graph`

**Signature:**
```python
def traverse_graph(graph, order=None, visited=None) -> list
```

**Input:**
- `graph` — the entry node's graph structure (from Stage 4)
- `order` — accumulator list (internal recursion; callers pass `None` or omit)
- `visited` — set of already-visited node IDs (internal recursion)

**Output:** A flat ordered list of node dicts in DFS preorder. Shared nodes appear exactly once, at the position they are first encountered.

**Responsibility:** Produce the definitive execution order for the DSL Builder. Every `START`, `INPUT`, `ACTION`, and `OUTPUT` node will appear once. `START` and `END` nodes appear in the list but are skipped by the DSL Builder since they emit no task blocks.

**Implementation pattern:**
```python
if order is None:
    order = []
if visited is None:
    visited = set()

node_id = graph["node"]["id"]
if node_id in visited:
    return order                         # shared node already appended; skip

visited.add(node_id)
order.append(graph["node"])             # append the node itself

for child in graph["children"]:
    traverse_graph(child, order, visited)

return order
```

**Critical rule:** Do NOT produce the execution order by iterating `workflow["nodes"]` (the raw JSON array). The raw array has no guaranteed order and no graph semantics. `traverse_graph()` is the only authoritative source of execution order.

---

## Stage 7 — DSL Builder (Not Yet Implemented)

**Planned signature:**
```python
def build_dsl(traversal_order: list) -> dict
```

**Input:** The ordered node list from Stage 6

**Output:** A Zigflow DSL dict with `document` and `do` keys

**Responsibility:** Convert each node in the traversal order into its Zigflow DSL task block. Dispatches to per-node-type builder functions. Skips `START` and `END` nodes.

**Planned per-node builders:**

```python
def build_input_node(node: dict) -> dict:
    ...  # returns a Zigflow `set` task dict

def build_action_node(node: dict) -> dict:
    ...  # returns a Zigflow activity call task dict

def build_output_node(node: dict) -> dict:
    ...  # returns a Zigflow `set` task dict
```

**Constraint:** All builder functions must be pure. No side effects, no global state.

---

## `compile` — Entry Point

**Signature:**
```python
def compile(workflow: dict) -> None   # currently; planned to return dict
```

**Responsibility:** Orchestrate all pipeline stages in order. Currently prints debug output. Will return the Zigflow DSL dict once the DSL Builder is implemented.

**Current implementation:**
```python
def compile(workflow: dict):
    node_map = generate_node_map(workflow)
    adjaceny = generate_adjaceny_list(workflow)
    starting_point = find_entrypoint(node_map)
    graph = generate_graph_structure(starting_point, node_map, adjaceny)
    print_graph(graph)
    traversal_order = traverse_graph(graph)
    print(traversal_order)
```

**Planned return value:** Full Zigflow DSL dict, e.g.:
```python
{
  "document": {
    "dsl": "1.0.0",
    "taskQueue": "zigflow",
    "workflowType": "compiled-workflow",
    "version": "1.0.0"
  },
  "do": [
    {"captureInput": {"set": {"user_name": "${ $input.name }"}}},
    {"greet": {"call": "activity", "with": {"name": "greet", ...}}},
    {"exposeOutput": {"set": {"message": "${ $context.message }"}}}
  ]
}
```

---

## Key Rules (Non-Negotiable)

1. **Do not iterate `workflow["nodes"]` for execution order.** Use `traverse_graph()` only.
2. **Do not instantiate classes** at any pipeline stage. All functions are module-level.
3. **Shared nodes must appear once in the output.** The `visited` set in `traverse_graph()` guarantees this.
4. **Traversal is DFS preorder.** A node is appended before its children are visited.
5. **`print_graph()` is debug-only.** It must not affect the pipeline output.
6. **Builder functions are pure.** No network calls, no filesystem access, no global mutation.
