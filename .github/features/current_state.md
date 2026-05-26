# DSL Compiler — Current State

## Version

V1 — POC complete. Pure-function pipeline validated end-to-end.

---

## Implemented Node Types

| Node | Builder | DSL task | Status |
|---|---|---|---|
| `START` | `terminal_builder.build_terminal` | none (returns `None`) | ✅ |
| `END` | `terminal_builder.build_terminal` | none (returns `None`) | ✅ |
| `INPUT` | `input_builder.build_input` | `set` | ✅ |
| `ACTION` | `action_builder.build_action` | `call: http` | ✅ |
| `OUTPUT` | `output_builder.build_output` | `set` | ✅ |
| `WAIT` | `wait_builder.build_wait` | `wait` | ✅ |

---

## Deferred Node Types

| Node | Planned DSL task | Reason deferred |
|---|---|---|
| `IF` | `switch` | Conditional branching — V2 |
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

| Stage | Function | Status |
|---|---|---|
| Node map | `generate_node_map()` | ✅ |
| Adjacency list | `generate_adjaceny_list()` | ✅ (intentional typo — do not rename) |
| Entrypoint detection | `find_entrypoint()` | ✅ |
| Graph structure | `generate_graph_structure()` | ✅ |
| Traversal | `traverse_graph()` | ✅ |
| DSL generation | `generate_dsl()` | ✅ |
| Serialization | `save_dsl()` | ✅ |
| Batch validation | `validate_outputs.py` | ✅ |

---

## Known Limitations (V1)

- ACTION node always targets `http://localhost:8080/{operation}` — host is hardcoded
- ACTION node always uses `method: post` — no other HTTP methods in V1
- No YAML output — JSON only
- No API server — compiler runs as a CLI tool only
- No sub-workflow support — `WORKFLOW` node type deferred

---

## Workflow Generator

- **File:** `poc-dsl-compiler/workflow_generator.py`
- **Status:** ✅ 7 difficulty levels implemented and validated
- **Run:** `python3 poc-dsl-compiler/workflow_generator.py`
- Prompts for level 1–7; writes Mermaid to `poc-dsl-compiler/workflows/` and JSON to `poc-dsl-compiler/workflow_outputs/`
- Generator output is **separate** from compiler input (`input/workflow_outputs/`) — copy manually to compile
- Full documentation: `.github/features/workflow_generator.md`

| Level | Shape | Nodes | Edges | WAIT? |
|---|---|---|---|---|
| 1 | Linear | 5 | 4 | — |
| 2 | 2 parallel branches | 7 | 7 | — |
| 3 | 3 parallel branches | 9 | 10 | — |
| 4 | 2 deep-chained branches | 9 | 9 | — |
| 5 | Mixed depth (branch 2 has own INPUT) | 10 | 10 | — |
| 6 | Linear with WAIT | 6 | 5 | ✅ |
| 7 | 2 branches with WAITs | 10 | 10 | ✅ |

---

## Current Milestone Pipeline

```
UI Workflow JSON  {nodes, edges}
        ↓
compiler.py
  generate_node_map()          →  {id: node_dict}
  generate_adjaceny_list()     →  {source_id: [target_id, ...]}
  find_entrypoint()            →  START node ID
  generate_graph_structure()   →  recursive DAG (dedup via visited set)
  traverse_graph()             →  DFS preorder ordered list of node dicts
        ↓
dsl_generator.py
  generate_dsl_boilerplate()   →  {document: {...}, do: []}
  NODE_BUILDERS dispatch       →  per-node DSL fragments appended to do list
        ↓
output/workflow_N_output_dsl_schema.json
        ↓
validate_outputs.py
  zigflow validate             →  must pass (exit 0)
```
