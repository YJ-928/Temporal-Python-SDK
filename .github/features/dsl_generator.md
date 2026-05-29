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
from builders.parallel_builder import build_parallel  # used in special dispatch (not NODE_BUILDERS)

NODE_BUILDERS = {
    "START":  build_terminal,
    "INPUT":  build_input,
    "ACTION": build_action,
    "OUTPUT": build_output,
    "WAIT":   build_wait,
    "IF":     build_if,
    "END":    build_terminal,
    # PARALLEL intentionally absent — handled by special dispatch in generate_dsl()
}
```

**When adding a new node type:** add import + entry in `NODE_BUILDERS`. **Exception:** if the node requires recursive branch pre-building (like PARALLEL), add a special dispatch block at the top of the `for entry in traversal:` loop instead.

### `generate_dsl(traversal, compiler_context=None, dsl_version="1.0.0", version="1.0.0", workflow_type="compiled-workflow", task_queue="zigflow") -> dict`

- Takes the `list[TraversalEntry]` from `run_compiler()["traversal"]`.
- `compiler_context`: **deprecated**. Always `None` or `{}`. Accepted for call-site compatibility; not read by any builder. Do not remove it.
- Calls `generate_dsl_boilerplate(...)` to create the document header with empty `do` list.
- Iterates the `TraversalEntry` list; for each entry:
  - **PARALLEL special dispatch** (checked first, before `NODE_BUILDERS`):
    - Reads `parallel_map` from the entry.
    - Calls `_build_do_list(branch_entry["traversal"], compiler_context)` for each branch to pre-build the branch do-list.
    - Calls `build_parallel(node, traversal_entry=entry, branch_do_lists={...})` with the pre-built lists.
    - PARALLEL is NOT in `NODE_BUILDERS` because building branches requires recursive `_build_do_list()` calls before the builder runs, which cannot be done inside the builder without importing `dsl_generator.py`.
  - **All other node types:** `builder = NODE_BUILDERS.get(node_type)` — then `builder(entry["node"], traversal_entry=entry, compiler_context=compiler_context)`.
  - Builders use `entry["is_terminal"]` to self-inject `then: end`.
  - IF builder uses `entry["branch_map"]` for goto routing.
  - OUTPUT builder uses `entry.get("reads_from_context")` to decide `${ $context.<field> }` vs `${ .<field> }`.
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

### `_build_do_list(branch_traversal: list, compiler_context=None) -> list`

**Internal helper** (not exported, not part of Phase A/B boundary). Produces a flat list of DSL task dicts for a single PARALLEL branch.

- Accepts a branch traversal list (a `list[TraversalEntry]` scoped to one branch, stored in `parallel_map[branch_id]["traversal"]`).
- Mirrors `generate_dsl()`'s inner loop but **returns a list** (no boilerplate, no `document` header).
- Handles nested PARALLEL by calling itself recursively: detects `node_type == "PARALLEL"`, pre-builds inner branch do-lists, calls `build_parallel()`.
- Used in two places:
  1. In `generate_dsl()` — for top-level PARALLEL branches.
  2. In itself recursively — for nested PARALLEL within branches.
- Unknown types inside a branch print `[WARNING]` and are skipped; does not crash.

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
    { "<nodeId>_parallel":    { "fork": { "compete": false, "branches": [ { "branch_0": { "do": [...] } }, { "branch_1": { "do": [...] } } ] } } },
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
- Do not add PARALLEL to `NODE_BUILDERS` — it uses special dispatch because it requires recursive `_build_do_list()` calls before builder invocation.
