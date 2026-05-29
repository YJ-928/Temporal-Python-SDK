# DSL Generator — Agent Reference

## What it is

`poc-dsl-compiler/dsl_generator.py` is the **Phase B DSL assembler**. It receives a pre-computed `list[TraversalEntry]` from Phase A (`compiler.py`), dispatches each entry to its typed builder function, and assembles the final Zigflow DSL document.

It is not a builder itself — it orchestrates builders. The distinction matters: builders produce individual DSL fragments; the assembler composes them into the complete `do` list.

It does **not** read graph structure, adjacency, node_map, or any graph internals. Everything it needs is pre-computed in the `TraversalEntry` dicts produced by `compiler.py`. The Phase A / Phase B boundary is the `list[TraversalEntry]`.

---

## File: `dsl_generator.py`

### Imports and dispatch table

```python
from builders.dsl_boilerplate_builder import generate_dsl_boilerplate
from builders.terminal_builder import build_terminal
from builders.input_builder import build_input
from builders.action_builder import build_action
from builders.output_builder import build_output
from builders.wait_builder import build_wait
from builders.if_builder import build_if

NODE_BUILDERS = {
    "START":  build_terminal,
    "INPUT":  build_input,
    "ACTION": build_action,
    "OUTPUT": build_output,
    "WAIT":   build_wait,
    "IF":     build_if,
    "END":    build_terminal,
}
```

**When adding a new node type:** add import + entry here. That is the only required change in this file.

### `generate_dsl(traversal, compiler_context=None, dsl_version="1.0.0", version="1.0.0", workflow_type="compiled-workflow", task_queue="zigflow") -> dict`

- Takes the `list[TraversalEntry]` from `run_compiler()["traversal"]`.
- `compiler_context`: **deprecated**. Always `None` or `{}`. Accepted for call-site compatibility; not read by any builder. Do not remove it.
- Calls `generate_dsl_boilerplate(...)` to create the document header with empty `do` list.
- Iterates the `TraversalEntry` list; for each entry:
  - Reads `entry["node_type"]` to look up the builder in `NODE_BUILDERS`.
  - Calls `builder(entry["node"], traversal_entry=entry, compiler_context=compiler_context)`.
  - Builders use `entry["is_terminal"]` to self-inject `then: end`.
  - IF builder uses `entry["branch_map"]` for goto routing.
- Unknown type → prints `[WARNING]` and skips (does not crash).
- Builder returns `None` (START/END) → skipped silently.
- Builder returns a dict → appended to `dsl["do"]`.
- Returns the complete DSL dict.

**Default parameter values** (passed through from `main.py`, overridable):
```python
compiler_context = None   # deprecated
dsl_version      = "1.0.0"
version          = "1.0.0"
workflow_type    = "compiled-workflow"
task_queue       = "zigflow"
```

### `save_dsl(dsl, output_path) -> None`

- Creates parent directories if missing (`os.makedirs(..., exist_ok=True)`).
- Writes JSON with `indent=2` and `encoding="utf-8"`.

---

## DSL Output Shape

Every generated DSL file looks like this:

```json
{
  "document": {
    "dsl": "1.0.0",
    "taskQueue": "zigflow",
    "workflowType": "compiled-workflow",
    "version": "1.0.0",
    "metadata": {}
  },
  "do": [
    { "<nodeId>_capture":     { "set":  { ... } } },
    { "<nodeId>_<operation>": { "call": "http", "with": { ... }, "output": { ... } } },
    { "<nodeId>_wait":        { "wait": { "seconds": 30 } } },
    { "<nodeId>_expose":      { "set":  { ... } } }
  ]
}
```

`do` is a **list of single-key dicts**. Each dict contains exactly one task. Order matches DFS preorder traversal. START and END nodes are absent — they emit no tasks.

---

## Output File Naming

Handled in `main.py`, not in `dsl_generator.py`:

| Input filename | Output filename |
|---|---|
| `workflow_1_output.json` | `output/workflow_1_dsl_schema.json` |
| `workflow_6_output.json` | `output/workflow_6_dsl_schema.json` |
| `my_flow.json` | `output/my_flow_dsl_schema.json` |

Rule: strip `_output` suffix if present, append `_dsl_schema.json`. No overwriting — each input gets its own output file.

---

## What NOT to do in dsl_generator.py

- Do not add graph traversal logic here — that belongs in `compiler.py`.
- Do not inline builder logic here — each node type has its own builder file.
- Do not add a class or a registry pattern — the dispatch table (`NODE_BUILDERS` dict) is the only dispatch mechanism.
- Do not crash on unknown node types — print a warning and skip.
