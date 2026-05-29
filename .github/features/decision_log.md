# Decision Log

Architectural decisions for the DSL compiler. Each entry records what was decided, why, and what was rejected. This is the "why" companion to the "what" in `dsl_compiler.md` and `current_state.md`.

---

## 2026-05 — Pure function compiler

**Decision:** All compiler and builder code is pure module-level functions. No classes.

**Reason:**
- Avoids framework lock-in — pure functions need no instantiation, no lifecycle, no dependency injection
- Easier to test: call a function, inspect the return value
- Easier to read: data flows in, data flows out, no hidden state
- Easier to extend: add a file, add a function, register it

**Rejected:**
- Class registry pattern — would require instantiating builders, managing lifecycles, and creating coupling between the registry and the builder classes
- Plugin system — premature abstraction for a POC; add when there is a demonstrated need

**Accepted:**
- `NODE_BUILDERS` dispatch dict as the single dispatch mechanism
- One Python file per node type in `builders/`

---

## 2026-05 — Dispatch table, not inheritance

**Decision:** `dsl_generator.py` dispatches to builders via `NODE_BUILDERS = {"TYPE": build_fn}`. No base class, no interface, no abstract method.

**Reason:**
- Dispatch dict is explicit — you can read the entire routing at a glance
- Adding a new node type is one import + one dict entry
- No inheritance hierarchy to maintain

**Rejected:**
- Abstract base class `NodeBuilder` with `build(node)` method — adds boilerplate and coupling for no benefit in a pure-function codebase

---

## 2026-05 — Templates are documentation only

**Decision:** Files in `poc-dsl-compiler/templates/` are never imported, loaded, or executed at runtime.

**Reason:**
- Templates were created to document intended DSL output shapes before builders existed
- Rendering templates at runtime would add a dependency (Jinja2, string formatting, loading) that builders do not need
- Builders produce the DSL directly; templates serve as reference fragments

**Consequence:**
- Template and builder must stay synchronized — if they disagree, the builder is the source of truth
- Templates for deferred node types document the intended future DSL shape but have no corresponding builder yet

**Rejected:**
- Jinja2 template rendering pipeline — adds a runtime dependency for no functional gain over direct dict construction

---

## 2026-05 — Compiler owns graph, generator owns assembly

**Decision:** Hard boundary between `compiler.py` (graph pipeline) and `dsl_generator.py` (DSL assembly).

**Reason:**
- Traversal order is a graph concern; DSL shape is a schema concern
- Separating them means each can be changed independently
- Compiler does not need to know about Zigflow; generator does not need to know about graph algorithms

**Rejected:**
- Single `compile_to_dsl()` function doing both traversal and DSL construction — would grow into an unmaintainable monolith

---

## 2026-05 — WAIT node emits DSL only

**Decision:** `wait_builder.py` emits `{"wait": {"seconds": N}}` and nothing more. Timer durability, crash recovery, and execution are entirely Zigflow + Temporal runtime concerns.

**Reason:**
- Builders are serialization-only; runtime behavior is not their domain
- Documenting runtime semantics inside a builder conflates two separate concerns
- A builder author should think about DSL shape, not execution model

---

## 2026-05 — WAIT extended with modes (duration and listen)

**Decision:** WAIT remains a single node type. Execution behaviour is selected via `data.mode` (`"duration"` or `"listen"`). No new node types are created.

**Reason:**
- Both `wait` and `listen` are temporal-pause constructs; they share the same semantic position in a graph (block until condition met)
- Creating separate `EVENT`, `SIGNAL`, or `WAIT_LISTEN` node types would add node-type surface area without changing the compiler, traversal, or dispatch table
- The builder is the correct layer for DSL dispatch; the compiler is unaware of modes

**Rejected:**
- Separate `WAIT_LISTEN` node type — unnecessary node-type proliferation; no graph algorithm benefit
- `signal` key on the WAIT node alongside `duration` — ambiguous schema; a single `mode` discriminator is cleaner

**Schema:**
```json
{ "type": "WAIT", "data": { "mode": "duration", "config": { "minutes": 5 } } }
{ "type": "WAIT", "data": { "mode": "listen",   "config": { "signal": "approval_received" } } }
```

**Backward compatibility:** Old schema (`data.duration`) is supported by the builder via a fallback check. Existing input files (`workflow_6_output.json`, `workflow_7_output.json`) compile correctly without modification.

**DSL output:**
- `mode: duration` → Zigflow `wait` task: `{"wait": {"minutes": 5}}`
- `mode: listen`   → Zigflow `listen` task: `{"listen": {"to": {"one": {"with": {"id": "approval_received"}}}}}`

**Files changed:** `builders/wait_builder.py` only. `compiler.py`, `dsl_generator.py`, and `NODE_BUILDERS` dispatch table are unchanged.

**Consequence:**
- Documentation (builders.md, dsl_compiler.md) uses "emits a Zigflow wait task" rather than "runs as a durable Temporal timer"
- The distinction matters: future builders (IF, PARALLEL) must follow the same principle

---

## 2026-05 — Deferred node types (IF, PARALLEL, VARIABLE, WORKFLOW)

**Decision:** V1 implements START, END, INPUT, ACTION, OUTPUT, WAIT only.

**Reason:**
- V1 goal: validate the pure-function pipeline end-to-end with a representative node set
- IF and PARALLEL require conditional/branching DSL constructs (`switch`, `fork`) that need a different traversal model
- VARIABLE is useful but not required to prove the pipeline works
- WORKFLOW (sub-workflow invocation) requires a different execution model

**Status:** Deferred until architecture expansion. Not forbidden — implement when ready, following the 11-step checklist in `dsl_compiler.md`.

---

## 2026-05 — dsl_generator is an assembler, not a builder

**Decision:** Rename mental model: `dsl_generator.py` is the **DSL assembler**, not the "master builder".

**Reason:**
- "Master builder" implies it builds DSL content — it does not; individual builders do
- "Assembler" accurately describes its role: receive traversal, call builders, compose the final document
- The distinction prevents future agents from adding DSL fragment logic into `dsl_generator.py`

**Rule enforced:** `dsl_generator.py` must never contain node-specific DSL construction. If it does, extract to a builder.

---

## 2026-05 — IF node: switch DSL, enriched traversal entries, Phase A branch pre-computation

**Decision:** IF node emits a Zigflow `switch` task. Branch routing is pre-computed by Phase A (`traverse_graph()`) and stored in `traversal_entry["branch_map"]`. The IF builder reads only `traversal_entry["branch_map"]` — it never reads adjacency or node_map.

**IF DSL shape:**
```json
{
  "N3_if": {
    "switch": [
      {"case":    {"when": "${ .user_email != \"\" }", "then": "N4_task_name"}},
      {"default": {"then": "N6_other_task"}}
    ]
  }
}
```

**Adjacency model:**
- `adjacency[source].append((target_id, control))` — list of tuples (same as WAIT mode extension)
- Non-IF edges: `control=None`
- IF branch edges: `control={"branch": "true"}` or `control={"branch": "false"}`
- `make_edge(eid, src, tgt, control=None)` in workflow_generator emits `"control"` key only when not None

**Phase A pre-computation:** `traverse_graph()` computes `branch_map` for each IF node:
```python
traversal_entry["branch_map"] == {
    "true":  {"node_id": "N4", "task_name": "N4_greet"},
    "false": {"node_id": "N6", "task_name": "N6_skip"},
}
```
`resolve_task_name(node_map[target_id])` resolves each branch target's task name. The result is stored in the `TraversalEntry` before `dsl_generator.py` or any builder is called.

**`compiler_context` (deprecated):**
- `run_compiler()` returns `"builder_context": {}` (empty dict). Previously this contained adjacency + node_map for IF builder lookup.
- `generate_dsl(traversal, compiler_context=None, ...)` still accepts it for call-site compatibility.
- No builder reads `compiler_context`. It is retained as `{}` for future LOOP/PARALLEL work without breaking call sites.

**Rejected:**
- Re-reading adjacency in the IF builder at build time (old approach) — violated the Phase A/B boundary; created hidden coupling where builders understood graph structure
- Injecting `_branch_children` into traversal node dicts — would mutate shared READ-ONLY graph node dicts
- Separate `TRUE_BRANCH` / `FALSE_BRANCH` node types — unnecessary node-type proliferation

**Known limitation resolved:** The V1 concern about `generate_graph_structure()` mutating shared graph node dicts is eliminated. Graph node dicts are now READ-ONLY after construction; all traversal metadata lives in `TraversalEntry` objects which are new allocations per traversal step.

---

## 2026-05 — Enriched traversal entries (Option B)

**Decision:** `traverse_graph()` returns `list[TraversalEntry]` (enriched dicts), not `list[node_dict]` (raw nodes). Each `TraversalEntry` wraps the original graph node with pre-computed execution metadata: `is_terminal`, `branch_map`, `successors`, `incoming_edge_control`.

**Typed contract** (`utils/traversal_types.py`):
```python
class TraversalEntry(TypedDict):
    node_id:               str
    node_type:             str
    node:                  dict          # READ-ONLY — shared ref from memoised DAG
    is_terminal:           bool          # True when any direct successor is END
    successors:            list[str]     # direct successor node IDs
    incoming_edge_control: dict | None   # control dict from parent edge; None for START
    branch_map:            BranchMap | None  # IF nodes only
```

**Why:** The original `list[node_dict]` design caused three hacks that violated the Phase A/B boundary:
1. `dsl_generator.py` re-read `adjacency` to detect END neighbors (for `then: end` injection)
2. `if_builder.py` re-read `adjacency` and `node_map` to find branch target task names
3. `dsl_generator.py` called `next(iter(fragment))` to mutate the fragment after the builder returned it

All three hacks are eliminated by pre-computing the needed metadata in Phase A.

**Option A (rejected):** Thread `adjacency` and `node_map` into builders via `compiler_context`. Rejected because it makes builders graph-aware, violating the Phase A/B boundary more deeply than the hacks it replaced.

**Option B (chosen):** Phase A computes all needed execution metadata. Builders receive exactly what they need via `traversal_entry`. The Phase A/B boundary is clean: the only thing that crosses it is `list[TraversalEntry]`.

**Consequence:** `compiler.py` is more responsible. It now computes `is_terminal`, `branch_map`, `successors`, and `incoming_edge_control`. All graph topology decisions happen before `dsl_generator.py` is called.

---

## 2026-05 — `then: end` injection owned by builders

**Decision:** Each builder is responsible for adding `"then": "end"` to its DSL fragment when `traversal_entry["is_terminal"]` is True. `dsl_generator.py` does not perform this injection.

**Why:** Originally, `dsl_generator.py` detected END neighbors via adjacency lookup and then mutated the returned fragment using `next(iter(fragment))`. This broke the Phase A/B boundary (generator read graph data) and mutated builder output (unexpected side effect).

**Consequence:** Every builder (except `terminal_builder` which returns None) contains:
```python
if traversal_entry and traversal_entry["is_terminal"]:
    fragment[task_name]["then"] = "end"
```
**IF builder exception:** IF nodes are never terminal (they always route to branch targets, which eventually lead to END). `if_builder` does not inject `then: end`.

---

## 2026-05 — `$context` persistence via `export.as` in INPUT and ACTION

**Decision:** INPUT builder exports all captured variables into `$context` via `export.as`. ACTION builder reads inputs from `$context` (not transient flowing data) and also exports its output into `$context`.

**Pattern:**
- INPUT: `export.as: ${ $context + {var1: .var1, var2: .var2} }`
- ACTION body: `{param: "${ $context.ctx_var }"}`
- ACTION: `export.as: ${ $context + {output_var: .output_var} }`

**Why:** Zigflow `call: http` tasks replace the current flowing data context with the HTTP response via `output.as`. Without `export.as`, variables captured by INPUT (or previous ACTION) would be lost after the first HTTP call. Reading inputs from `$context` ensures they remain accessible regardless of how many prior ACTION tasks have replaced the data context.

**Consequence:** Chained ACTION nodes and parallel branches can always access all previously captured variables from `$context`, not just those in the immediate prior task's output.

**Rejected:** Reading inputs from `${ .<var> }` (transient data) — would silently produce empty values after any preceding `call: http` task.

---

**Schema:**
```json
{ "id": "N3", "type": "IF", "condition": { "left": "user_email", "operator": "!=", "right": "" } }
```

**Nested IF with parent data:**
```json
{ "id": "N4", "type": "IF", "condition": { "left": "email_verified", "operator": "==", "right": true }, "data": { "parent_field": "..." } }
```

**Reason:**
- `condition` is not operational data about the node — it is the branching predicate, a first-class concern of the IF type. Placing it at root makes this distinction explicit.
- `data` is reserved for node-specific operational payload (e.g., parent-scoped values passed into a nested IF). Keeping them separate prevents `data` from becoming a catch-all.
- For simple IF nodes `data` is omitted entirely, keeping the schema minimal.
- `if_builder.py` reads `node["condition"]` directly — no intermediate `data` access needed.

**Consequence:** All IF node input JSON fixtures use root-level `condition`. `workflow_10_output.json` and `workflow_11_output.json` migrated. `make_if()` in `workflow_generator.py` emits root-level `condition`.

**Rejected:** `data.condition` wrapper — obscures the structural role of the condition; makes `data` semantically ambiguous.

---

## 2026-05 — condition_builder.py as shared utility

## 2026-05 — condition_builder.py as shared utility

**Decision:** Extract condition expression building into `builders/condition_builder.py → build_condition_expression(condition: dict) -> str`.

**Reason:**
- IF builder previously contained an inline f-string for jq expression construction
- The same expression format will be needed by LOOP, conditional WAIT, and any other node that evaluates a condition
- Centralising the expression format in one file means operator support (adding `in`, `not in`, etc.) is a one-file change
- Operator validation (`SUPPORTED_OPERATORS` frozenset) is now explicit and discoverable

**Consequence:**
- `if_builder.py` imports from `condition_builder.py` — this is the correct direction (builder → utility)
- `condition_builder.py` does not import from any builder or from `compiler.py` — it is a leaf utility
- Future node builders that need conditions should import `build_condition_expression`, not reimplement it

**Rejected:** Keeping the f-string inline in `if_builder.py` — breaks reuse; each future conditional builder would need its own copy.

---

## 2026-05 — Level 11: nested IF validation

**Decision:** Add Level 11 to the workflow generator (nested IF topology) as the end-to-end validation for nested `switch` DSL goto routing.

**Topology:**
```
START → INPUT(email)
      → IF outer (user_email != "") → [true]  → IF inner (email_verified == "true")
                                                    → [true]  → send_notification → OUTPUT → END
                                                    → [false] → send_email        → OUTPUT → END
                                      → [false] → log_missing_email → OUTPUT → END
```

**What this validates:**
- Nested switch tasks in flat Zigflow DSL (goto routing handles nesting implicitly via task-name references)
- Branch map pre-computation by Phase A `traverse_graph()` for nested IF nodes (both outer and inner IF have their `branch_map` resolved before any builder is called)
- DFS preorder traversal correctly orders: outer IF → inner IF → true branch → false branch → outer false branch
- `resolve_task_name()` resolves IF-to-IF goto correctly (`N4_if`)
- All 11 difficulty levels validated: `python3 validate_outputs.py` — all pass `zigflow validate`

**Zigflow validation result:** ✅ `workflow_11_dsl_schema.json` passes `zigflow validate`

---

## 2026-05 — Compiler does not validate generator output

**Decision:** The compiler assumes workflow JSON produced by the generator is structurally valid. It does not explicitly validate graph constraints before traversal.

**Reason:**
- Generator enforces constraints (one START, one END, no orphan nodes) during generation
- Adding validation in the compiler would duplicate logic and slow the pipeline
- V1 is a POC; explicit validation is a V2 concern

**Risk:** Violations in the input JSON cause undefined traversal behavior (silent errors or wrong DSL), not explicit errors.

**Consequence:** Explicit input validation should be added before the compiler is used with untrusted input (e.g., arbitrary user-submitted JSON from a UI).
