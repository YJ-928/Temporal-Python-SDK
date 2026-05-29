# DSL Compiler — Current State

## Version

V1 — POC complete. Pure-function pipeline validated end-to-end.

---

## Implemented Node Types

| Node | Builder | DSL task | Status |
|---|---|---|-|
| `START` | `terminal_builder.build_terminal` | none (returns `None`) | ✅ |
| `END` | `terminal_builder.build_terminal` | none (returns `None`) | ✅ |
| `INPUT` | `input_builder.build_input` | `set` | ✅ |
| `ACTION` | `action_builder.build_action` | `call: http` | ✅ |
| `OUTPUT` | `output_builder.build_output` | `set` | ✅ |
| `WAIT` | `wait_builder.build_wait` | `wait` (duration mode) or `listen` (listen mode) | ✅ |
| `IF` | `if_builder.build_if` | `switch` (case/when/then + default/then) | ✅ |

**IF node schema:** `condition` is a root-level key on the IF node (same level as `id`, `type`, `data`). `data` is optional — omitted for simple IF nodes; present when a nested IF receives parent-scoped values. Expression building is delegated to `builders/condition_builder.py → build_condition_expression(condition)`.

```json
{ "id": "N3", "type": "IF", "condition": { "left": "user_email", "operator": "!=", "right": "" } }
```

Nested IF with parent data:
```json
{ "id": "N4", "type": "IF", "condition": { "left": "email_verified", "operator": "==", "right": true }, "data": { "parent_field": "..." } }
```

**Shared utility:** `builders/condition_builder.py` — `build_condition_expression(condition: dict) -> str`. Converts a condition dict to a Zigflow jq expression string (e.g. `${ .user_email != "" }`). Reusable by any future node type that evaluates a condition (LOOP, etc.). Validates operator against `SUPPORTED_OPERATORS` frozenset.

---

## Deferred Node Types

| Node | Planned DSL task | Reason deferred |
|---|---|---|
| `PARALLEL` | `fork` | Parallel execution — V2 |
| `VARIABLE` | `set` | Variable binding — V2 |
| `WORKFLOW` | `run: workflow` | Sub-workflow invocation — V2 |

---

## Validation Status

- All output files in `poc-dsl-compiler/output/` pass `zigflow validate`
- Run: `python3 poc-dsl-compiler/validate_outputs.py`
- Exit code 0 = all pass. Exit code 1 = one or more failures.

---

## Output Format

- JSON only (`.json`)
- Files named: `workflow_N_dsl_schema.json`
- Location: `poc-dsl-compiler/output/`
- Each input file gets its own output file — no overwriting between runs

---

## Pipeline Status

| Stage | Function | Owner | Status |
|---|---|---|---|
| Node map | `generate_node_map()` | Phase A | ✅ |
| Adjacency list | `generate_adjaceny_list()` | Phase A | ✅ (intentional typo — do not rename); tuples `(target_id, control)` — `control=None` for non-IF edges, `{"branch": "true"|"false"}` for IF branch edges |
| Entrypoint detection | `find_entrypoint()` | Phase A | ✅ |
| Graph structure | `generate_graph_structure()` | Phase A | ✅ node dicts are READ-ONLY after construction — shared refs in memoised DAG |
| Traversal | `traverse_graph()` | Phase A | ✅ returns `list[TraversalEntry]`; computes `is_terminal`, `branch_map`, `successors`, `incoming_edge_control` |
| DSL generation | `generate_dsl()` | Phase B | ✅ iterates `TraversalEntry` list; no graph reads |
| Serialization | `save_dsl()` | Phase B | ✅ |
| Batch validation | `validate_outputs.py` | — | ✅ |

---

## Known Limitations (V1)

- ACTION node always targets `http://localhost:8080/{operation}` — host is hardcoded
- ACTION node always uses `method: post` — no other HTTP methods in V1
- No YAML output — JSON only
- No API server — compiler runs as a CLI tool only
- No sub-workflow support — `WORKFLOW` node type deferred
- **Reconvergence (JOIN/diamond patterns) not supported:** when two branches converge on a shared node (one node with two incoming edges from different paths), `traverse_graph()` visits it from the first DFS path only. The second path sees it already in `visited` and skips it. The compiled DSL will be missing the reconvergent node for one branch. No JOIN semantics are implemented.
- **PARALLEL not implemented:** no `fork` task generation. The `PARALLEL` node type is deferred to V2.
- **LOOP/cycle not implemented:** no cycle detection beyond the `visited` set deduplication used for DAG shared-node memoisation. Cyclic graphs are not supported.
- **`builder_context` deprecated:** `run_compiler()` returns `builder_context: {}` (empty dict) for call-site compatibility. No builder reads it. Reserved for future LOOP/PARALLEL work without breaking call sites.
- **No input validation:** the compiler assumes well-formed generator output (one START, one END, no orphan nodes). Malformed JSON from untrusted sources (e.g., arbitrary UI input) will cause undefined traversal behaviour, not explicit errors.

---

## Workflow Generator

- **File:** `poc-dsl-compiler/workflow_generator.py`
- **Status:** ✅ 11 difficulty levels implemented and validated
- **Run:** `python3 poc-dsl-compiler/workflow_generator.py`
- Prompts for level 1–11; writes Mermaid to `poc-dsl-compiler/input/workflows/` and JSON to `poc-dsl-compiler/input/workflow_outputs/` (compiler's input directory — no manual copy needed)
- Full documentation: `.github/features/workflow_generator.md`

| Level | Shape | Nodes | Edges | WAIT mode |
|---|---|---|---|---|
| 1 | Linear | 5 | 4 | — |
| 2 | 2 parallel branches | 7 | 7 | — |
| 3 | 3 parallel branches | 9 | 10 | — |
| 4 | 2 deep-chained branches | 9 | 9 | — |
| 5 | Mixed depth (branch 2 has own INPUT) | 10 | 10 | — |
| 6 | Linear with WAIT(duration) | 6 | 5 | duration |
| 7 | 2 branches with WAIT(duration) | 10 | 10 | duration |
| 8 | Linear with WAIT(listen) | 6 | 5 | listen |
| 9 | 2 branches: branch A duration, branch B listen | 9 | 9 | duration + listen |
| 10 | Linear IF: email presence guard, true/false branches | 8 | 8 | — |
| 11 | Nested IF: outer email-presence guard; inner email-verified check in true branch | 11 | 12 | — |

---

## Current Milestone Pipeline

```
UI Workflow JSON  {nodes, edges}
        ↓
── PHASE A: Graph Compilation (compiler.py) ──────────────────────────────────
  generate_node_map()          →  {id: node_dict}
  generate_adjaceny_list()     →  {source_id: [(target_id, control), ...]}
  find_entrypoint()            →  START node ID
  generate_graph_structure()   →  recursive memoised DAG (shared nodes deduplicated)
  traverse_graph()             →  list[TraversalEntry] — DFS preorder
                                  Each entry: {node_id, node_type, node (READ-ONLY),
                                               is_terminal, successors,
                                               incoming_edge_control, branch_map (IF only)}
        ↓
── PHASE B: DSL Assembly (dsl_generator.py) ──────────────────────────────────
  generate_dsl_boilerplate()   →  {document: {...}, do: []}
  NODE_BUILDERS dispatch       →  builder(node, traversal_entry=entry) per entry
                                  Builders self-inject then:end via is_terminal
                                  IF builder reads branch_map for goto routing
        ↓
output/workflow_N_dsl_schema.json
        ↓
validate_outputs.py
  zigflow validate             →  must pass (exit 0)
```

**Phase boundary:** `compiler.py` is the sole producer of `TraversalEntry` dicts. `dsl_generator.py` and all builders must not read `adjacency`, `node_map`, or any other graph internals. Everything they need is pre-computed in the `TraversalEntry`.
