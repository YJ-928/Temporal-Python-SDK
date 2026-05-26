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
├── compiler.py              # Graph pipeline functions
├── dsl_generator.py         # NODE_BUILDERS dispatch + generate_dsl() + save_dsl()
├── validate_outputs.py      # Batch validator for all files in output/
├── builders/
│   ├── __init__.py
│   ├── terminal_builder.py      # START, END → None (no DSL)
│   ├── input_builder.py         # INPUT → set task
│   ├── action_builder.py        # ACTION → call: http task
│   ├── output_builder.py        # OUTPUT → set task
│   ├── wait_builder.py          # WAIT → wait task
│   └── dsl_boilerplate_builder.py  # DSL document header
├── input/
│   ├── workflow_outputs/    # ← all input JSON files live here
│   └── workflows/           # Mermaid diagram .md files
├── output/                  # Generated DSL files (auto-created, not committed)
├── templates/               # Reference schema fragments only — NOT used at runtime
├── examples/                # Legacy sample inputs (kept for reference)
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
    { "id": "N4", "type": "WAIT",   "data": { ... } },
    { "id": "N5", "type": "OUTPUT", "data": { ... } },
    { "id": "N6", "type": "END" }
  ],
  "edges": [
    { "id": "E1", "source": "N1", "target": "N2" },
    { "id": "E2", "source": "N2", "target": "N3" }
  ]
}
```

**Invariants:**
- `nodes` and `edges` are the only top-level keys.
- Every edge: exactly `{id, source, target}`. No business logic in edges.
- Node IDs must be unique. Edge endpoints must reference valid node IDs.
- Exactly one `START` node and one `END` node.

---

## compiler.py — Graph Pipeline

Five pure functions. All stateless. Called via `run_compiler(workflow)`.

| Function | Input | Output |
|---|---|---|
| `generate_node_map(workflow)` | raw workflow dict | `{node_id: node_dict}` |
| `generate_adjaceny_list(workflow)` | raw workflow dict | `{source_id: [target_id, ...]}` — note: intentional typo in name |
| `find_entrypoint(node_map)` | node_map | ID of the START node |
| `generate_graph_structure(entrypoint, node_map, adjacency)` | above | Recursive graph dict with deduplication |
| `traverse_graph(graph)` | graph root | Ordered list of node dicts (DFS preorder) |
| `run_compiler(workflow)` | raw workflow dict | `{node_map, adjacency, graph, traversal}` |

**Critical rules:**
- Never iterate the raw node array to determine execution order. Always use `traverse_graph()`.
- Shared nodes (multiple incoming edges in a DAG) are visited exactly once — `visited` set handles deduplication.
- Traversal order is **DFS preorder** from START.
- `generate_adjaceny_list` has an intentional typo in the function name — do not rename it.

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
| `INPUT` | ✅ | `set` | `input_builder.build_input` |
| `ACTION` | ✅ | `call: http` | `action_builder.build_action` |
| `OUTPUT` | ✅ | `set` | `output_builder.build_output` |
| `WAIT` | ✅ | `wait` | `wait_builder.build_wait` |
| `IF` | ❌ deferred | `switch` | not implemented |
| `PARALLEL` | ❌ deferred | `fork` | not implemented |
| `VARIABLE` | ❌ deferred | `set` | not implemented |
| `WORKFLOW` | ❌ deferred | `run: {workflow}` | not implemented |

**Do not implement deferred node types until the V1 pure-function approach is validated end-to-end.**

---

## Architecture Constraints

These constraints are permanent. Violations cause coupling that breaks the separation of concerns the compiler depends on.

### Compiler (`compiler.py`) owns:
- `node_map` — `{id: node_dict}` index of all nodes
- `adjacency` — `{source_id: [target_id, ...]}` edge map
- `graph` — recursive graph structure (deduplication via `visited` set)
- `traversal` — DFS preorder ordered list of node dicts

### DSL Generator (`dsl_generator.py`) owns:
- `NODE_BUILDERS` dispatch table — maps node type string → builder function
- DSL assembly — iterates traversal, calls builders, appends to `do` list
- Serialization — `save_dsl()` writes JSON to `output/`
- Boilerplate — calls `generate_dsl_boilerplate()` to create the document header

### Builders (`builders/*.py`) own:
- One responsibility: `node dict → DSL fragment dict`
- No graph knowledge, no traversal knowledge, no serialization
- No imports from `compiler.py` or `dsl_generator.py`

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

1. Create `builders/<type_lower>_builder.py` with a single `build_<type>(node: dict) -> dict` function.
2. Add the import and dispatch entry to `dsl_generator.py`:
   ```python
   from builders.<type_lower>_builder import build_<type>
   # in NODE_BUILDERS:
   "<TYPE>": build_<type>,
   ```
3. Update or create `templates/<type>.json` — synchronized with builder output (builder is source of truth).
4. Add difficulty level or node to `workflow_generator.py` vocabularies so it can generate test workflows.
5. Add or update an input JSON in `input/workflow_outputs/` that exercises the new node.
6. Run `python3 main.py <workflow>` then `python3 validate_outputs.py`. All outputs must pass `zigflow validate`.
7. Update `.github/features/dsl_compiler.md` node type table (this file).
8. Update `.github/features/builders.md` builder reference and template table.
9. Update `.github/features/current_state.md` implemented list.
10. Update `.github/features/decision_log.md` with the decision rationale.
11. Update `.github/copilot-instructions.md` if the checklist or rules change.
