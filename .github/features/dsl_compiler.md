# DSL Compiler — Agent Reference

## What it is

The DSL Compiler transforms a **UI workflow graph JSON** into a **Zigflow DSL JSON** that can be validated and executed by the Zigflow runtime on top of Temporal.

```
UI Workflow Builder
      ↓
JSON {nodes, edges}         ← input contract (see below)
      ↓
   compiler.py              ← graph pipeline (node_map, adjacency, traversal)
      ↓
  dsl_generator.py          ← dispatches each node to a typed builder
      ↓
Zigflow DSL JSON            ← output written to output/
      ↓
zigflow validate            ← schema validation (must always pass)
```

**Root:** `poc-dsl-compiler/`
**Entry point:** `poc-dsl-compiler/main.py`
**Rules:** Pure functions only. No classes. No global state. No templates used at runtime — templates in `templates/` are reference-only documentation.

---

## Directory Layout

```
poc-dsl-compiler/
├── main.py                  # Orchestrator entry point
├── compiler.py              # Phase A — graph pipeline (node_map, adjacency, TraversalEntry list)
├── dsl_generator.py         # Phase B — NODE_BUILDERS dispatch + generate_dsl() + save_dsl()
├── validate_outputs.py      # Batch validator for all files in output/
├── builders/
│   ├── __init__.py
│   ├── terminal_builder.py      # START, END → None (no DSL)
│   ├── input_builder.py         # INPUT → set task + export.as into $context
│   ├── action_builder.py        # ACTION → call: http; reads from $context; export.as
│   ├── output_builder.py        # OUTPUT → set task
│   ├── wait_builder.py          # WAIT → wait (duration) or listen (signal) task
│   ├── if_builder.py            # IF → switch task; reads branch_map from traversal_entry
│   ├── condition_builder.py     # Utility — build_condition_expression(); shared by IF and future nodes
│   └── dsl_boilerplate_builder.py  # DSL document header
├── utils/
│   ├── traversal_types.py       # TypedDicts: BranchTarget, BranchMap, TraversalEntry
│   └── task_names.py            # resolve_task_name(node) — pure utility used by compiler.py
├── input/
│   ├── workflow_outputs/    # ← all input JSON files live here
│   └── workflows/           # Mermaid diagram .md files
├── output/                  # Generated DSL files (auto-created, not committed)
├── templates/               # Reference schema fragments only — NOT used at runtime
└── docs/                    # Design docs
```

---

## Input JSON Contract (frozen V1)

```json
{
  "nodes": [
    { "id": "N1", "type": "START" },
    { "id": "N2", "type": "INPUT",  "data": { ... } },
    { "id": "N3", "type": "ACTION", "data": { ... } },
    { "id": "N4", "type": "WAIT",   "data": { "mode": "duration|listen", "config": { ... } } },
    { "id": "N5", "type": "OUTPUT", "data": { ... } },
    { "id": "N6", "type": "IF",     "condition": { "left": "field", "operator": "!=", "right": "" } },
    { "id": "N7", "type": "END" }
  ],
  "edges": [
    { "id": "E1", "source": "N1", "target": "N2" },
    { "id": "E2", "source": "N2", "target": "N3" },
    { "id": "E3", "source": "N6", "target": "N3", "control": { "branch": "true" } },
    { "id": "E4", "source": "N6", "target": "N5", "control": { "branch": "false" } }
  ]
}
```

**Invariants:**
- `nodes` and `edges` are the only top-level keys.
- Non-IF edges: exactly `{id, source, target}`. No business logic in edges.
- IF edges carry a `control` key: `{"id", "source", "target", "control": {"branch": "true"|"false"}}`. Exactly one `true` branch and one `false` branch per IF node.
- IF node: `condition` is a **root-level key** on the node (same level as `id`, `type`). `data` is optional and omitted for simple IF nodes.
- Node IDs must be unique. Edge endpoints must reference valid node IDs.
- Exactly one `START` node and one `END` node.

---

## compiler.py — Graph Pipeline (Phase A)

Six pure functions. All stateless. Called via `run_compiler(workflow)`.
This is **Phase A** — it owns all graph, topology, and execution-metadata concerns.

| Function | Input | Output |
|---|---|---|
| `generate_node_map(workflow)` | raw workflow dict | `{node_id: node_dict}` |
| `generate_adjaceny_list(workflow)` | raw workflow dict | `{source_id: [(target_id, control), ...]}` — intentional typo; `control=None` for normal edges, `{"branch": "true"|"false"}` for IF edges |
| `find_entrypoint(node_map)` | node_map | ID of the START node |
| `generate_graph_structure(entrypoint, node_map, adjacency)` | above | Recursive memoised DAG; graph node dicts are READ-ONLY shared references after construction |
| `traverse_graph(graph, adjacency, node_map, ...)` | graph root + adjacency + node_map | `list[TraversalEntry]` (DFS preorder); each entry pre-computes `is_terminal`, `branch_map` (IF only), `successors`, `incoming_edge_control` |
| `run_compiler(workflow)` | raw workflow dict | `{node_map, adjacency, graph, traversal: list[TraversalEntry], builder_context: {}}` |

**Critical rules:**
- Never iterate the raw node array to determine execution order. Always use `traverse_graph()`.
- Shared nodes (multiple incoming edges in a DAG) are visited exactly once — `visited` set handles deduplication.
- Traversal order is **DFS preorder** from START.
- `generate_adjaceny_list` has an intentional typo in the function name — do not rename it.
- Graph node dicts are **READ-ONLY** after `generate_graph_structure()`. They are shared references in the memoised DAG. Never attach traversal-step metadata to them — use `TraversalEntry` instead.
- `builder_context` in `run_compiler()` return dict is **deprecated** (`{}`). No builder reads it. Retained for call-site compatibility while LOOP/PARALLEL stabilise.

**TraversalEntry contract** (defined in `utils/traversal_types.py`):
```python
class TraversalEntry(TypedDict):
    node_id:               str       # shortcut — avoids entry["node"]["id"] everywhere
    node_type:             str       # shortcut — avoids entry["node"]["type"]
    node:                  dict      # READ-ONLY; original node dict from graph
    is_terminal:           bool      # True when any direct successor is END
    successors:            list[str] # direct successor node IDs
    incoming_edge_control: dict | None  # control dict from parent edge; None for START
    branch_map:            BranchMap | None  # IF nodes only; None for all others
```

---

## main.py — Entry Point

```
python3 main.py                          # default: input/workflow_outputs/workflow_1_output.json
python3 main.py workflow_4_output        # resolved from input/workflow_outputs/ (.json added automatically)
python3 main.py workflow_4_output.json   # same, extension already present
python3 main.py /full/path/to/wf.json   # absolute path used directly
```

**Input resolution** (`resolve_input_path`):
1. No arg → `DEFAULT_INPUT` (`input/workflow_outputs/workflow_1_output.json`)
2. Absolute path → used as-is; raises `FileNotFoundError` if missing
3. Relative path that exists from cwd → used as-is
4. Bare name (with or without `.json`) → `input/workflow_outputs/{name}.json`; raises `FileNotFoundError` if not found

**Output naming** (`resolve_output_path`):
- Strips `_output` suffix from stem, appends `_dsl_schema.json`
- `workflow_1_output.json` → `output/workflow_1_dsl_schema.json`
- Each input gets its own output file — **no overwriting**

**Constants:**
```python
BASE       = os.path.dirname(__file__)
DEFAULT_INPUT = os.path.join(BASE, "input", "workflow_outputs", "workflow_1_output.json")
INPUT_DIR  = os.path.join(BASE, "input", "workflow_outputs")
OUTPUT_DIR = os.path.join(BASE, "output")
```

---

## validate_outputs.py — Batch Validator

Runs `zigflow validate` against every `.json` file in `output/`, prints per-file pass/fail, strips the update-available banner, and exits with code `1` if any file fails.

```bash
python3 poc-dsl-compiler/validate_outputs.py
```

---

## Valid Zigflow Task Types (v1.0.0)

Only these type names are schema-valid in Zigflow DSL v1.0.0:

`set` · `call` · `do` · `fork` · `for` · `listen` · `raise` · `run` · `switch` · `try` · `wait`

**Any other string as a task type will fail `zigflow validate`.**

---

## V1 Node Types (frozen)

| Node Type | Implemented | DSL task type | Builder |
|---|---|---|---|
| `START` | ✅ | none (returns None) | `terminal_builder.build_terminal` |
| `END` | ✅ | none (returns None) | `terminal_builder.build_terminal` |
| `INPUT` | ✅ | `set` + `export.as` | `input_builder.build_input` |
| `ACTION` | ✅ | `call: http` + `export.as` | `action_builder.build_action` |
| `OUTPUT` | ✅ | `set` | `output_builder.build_output` |
| `WAIT` | ✅ | `wait` (duration) or `listen` (signal) | `wait_builder.build_wait` |
| `IF` | ✅ | `switch` | `if_builder.build_if` |
| `PARALLEL` | ❌ deferred | `fork` | not implemented — V2 |
| `VARIABLE` | ❌ deferred | `set` | not implemented — V2 |
| `WORKFLOW` | ❌ deferred | `run: {workflow}` | not implemented — V2 |

**Known limitation:** reconvergence (diamond/JOIN patterns where two branches converge on one node) is not supported. See `current_state.md` Known Limitations.

---

## Architecture Constraints

These constraints are permanent. Violations cause coupling that breaks the separation of concerns the compiler depends on.

### Phase A — Compiler (`compiler.py`) owns:
- `node_map` — `{id: node_dict}` index of all nodes
- `adjacency` — `{source_id: [(target_id, control), ...]}` edge map (tuples carrying control metadata)
- `graph` — recursive memoised DAG; graph node dicts are READ-ONLY shared references
- `traversal` — `list[TraversalEntry]` in DFS preorder; the sole producer of this type
- All execution metadata: `is_terminal`, `branch_map` (IF nodes), `successors`, `incoming_edge_control`

### Phase B — DSL Generator (`dsl_generator.py`) owns:
- `NODE_BUILDERS` dispatch table — maps node type string → builder function
- DSL assembly — iterates `TraversalEntry` list, calls `builder(node, traversal_entry=entry)`, appends to `do` list
- Serialization — `save_dsl()` writes JSON to `output/`
- Boilerplate — calls `generate_dsl_boilerplate()` to create the document header
- **Must not** read `adjacency`, `node_map`, or any graph internals

### Builders (`builders/*.py`) own:
- One responsibility: `(node dict, traversal_entry) → DSL fragment dict`
- Self-inject `then: end` when `traversal_entry["is_terminal"]` is True
- IF builder reads `traversal_entry["branch_map"]` for goto routing — never re-reads adjacency
- No imports from `compiler.py` or `dsl_generator.py`
- `condition_builder.py` is a leaf utility (no builder/compiler imports); reusable by any conditional node

### Runtime (Zigflow + Temporal) owns:
- Execution of `call: http` tasks (HTTP, retries, timeouts)
- Execution of `wait` tasks (durable timers, crash recovery)
- Signal handling (`listen` tasks)
- Activity scheduling and heartbeats
- Event history and replay

### Forbidden — never cross these boundaries:
| What | Why |
|---|---|
| Builder importing from `compiler.py` | Breaks builder isolation |
| `compiler.py` importing from `builders/` | Breaks graph-layer purity |
| Runtime execution logic inside a builder | Builders describe DSL, not behavior |
| Graph generation inside `dsl_generator.py` | Graph ownership belongs to compiler |
| Templates imported or loaded at runtime | Templates are documentation only |
| Classes anywhere in `poc-dsl-compiler/` | All code is pure module-level functions |
| Registry or factory patterns | The `NODE_BUILDERS` dispatch dict is the only dispatch mechanism |

---

## How to Add a New Node Type

1. Create `builders/<type_lower>_builder.py` with a single `build_<type>(node: dict, *, traversal_entry=None, compiler_context=None) -> dict | None` function. Accept `traversal_entry` as a keyword-only arg. If the node can be terminal, inject `then: end` when `traversal_entry and traversal_entry["is_terminal"]`.
2. Add the import and dispatch entry to `dsl_generator.py`:
   ```python
   from builders.<type_lower>_builder import build_<type>
   # in NODE_BUILDERS:
   "<TYPE>": build_<type>,
   ```
3. If the node needs execution metadata (branch targets, etc.), add the required fields to `traverse_graph()` in `compiler.py`. Update `utils/traversal_types.py` TypedDict.
4. Update or create `templates/<type>.json` — synchronized with builder output (builder is source of truth).
5. Add vocabulary and `make_<type>()` to `workflow_generator.py`. Update `_node_label()` and `_edge_label()`.
6. Add a difficulty level in `workflow_generator.py` that exercises the new node type end-to-end.
7. Add or update an input JSON in `input/workflow_outputs/` that exercises the new node.
8. Run `python3 main.py <workflow>` then `python3 validate_outputs.py`. All outputs must pass `zigflow validate`.
9. Update `.github/features/dsl_compiler.md` node type table (this file).
10. Update `.github/features/builders.md` builder reference and template table.
11. Update `.github/features/current_state.md` implemented list.
12. Update `.github/features/decision_log.md` with the decision rationale.
13. Update `.github/copilot-instructions.md` if the checklist or rules change.
