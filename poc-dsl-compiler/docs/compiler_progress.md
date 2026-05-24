# Compiler Progress

> **Status:** POC — active development
> **Last updated:** May 2026

---

## Completed

### Pipeline Core
- [x] `generate_node_map(workflow)` — builds `{node_id → node}` index from raw JSON
- [x] `generate_adjacency_list(workflow)` — builds `{source_id → [target_id, ...]}` from edges
- [x] `find_entrypoint(node_map)` — locates the `START` node by type scan
- [x] `generate_graph_structure(entrypoint, node_map, adjacency, graph)` — builds a memoized recursive DAG representation; shared nodes appear once
- [x] `print_graph(graph, level, visited)` — DFS preorder debug visualisation with cycle-safe `[REF]` markers
- [x] `traverse_graph(graph, order, visited)` — produces the ordered execution list via DFS preorder; visited-set deduplication
- [x] `compile(workflow)` — top-level entry point wiring all stages together

### Graph Support
- [x] Linear (chain) graphs — `START → INPUT → ACTION → OUTPUT → END`
- [x] Branching graphs — one node with multiple outgoing edges (fan-out)
- [x] Shared nodes — a single node reached from multiple parents is visited once

### Sample Inputs
- [x] `workflow_1_output.json` — simple linear hello-world workflow
- [x] `workflow_2_output.json` — branching workflow with two OUTPUT paths and a shared END

### Mermaid
- [x] `workflow_1.md` and `workflow_2.md` — Mermaid graph diagrams for visual inspection

### Workflow Generator
- [x] `generate_input(node_id)` — generates a random INPUT node
- [x] `generate_action(node_id, previous_node)` — generates an ACTION node wired to a previous variable
- [x] `generate_output(node_id)` — generates an OUTPUT node
- [x] `generate_node(node_id, node_type, previous)` — dispatcher for all node generators
- [x] `generate_workflow(total_nodes, branches)` — produces a complete random workflow JSON
- [x] `generate_mermaid(workflow)` — converts a workflow to a Mermaid `graph TD` string
- [x] `save_workflow(workflow, folder)` — writes `workflow.json` + `workflow.md` to `generated/`
- [x] CLI entry point — prompts for `Total Nodes` and `Branches`, saves output

### Documentation
- [x] `01_existing_poc_analysis.md` — V0 analysis
- [x] `02_graph_schema_v1.md` — earlier graph schema draft
- [x] `03_node_mapping.md` — earlier node → DSL mapping reference
- [x] `04_compiler_pipeline_v1.md` — earlier three-stage pipeline design
- [x] `05_poc_scope.md` — earlier scope definition
- [x] `compiler_context.md` — authoritative V1 architecture document (this session)
- [x] `compiler_pipeline.md` — frozen current seven-stage pipeline (this session)
- [x] `compiler_progress.md` — this file (this session)
- [x] `workflow_json_contract.md` — frozen input JSON contract (this session)
- [x] `testing_strategy.md` — workflow generator and fuzz-testing approach (this session)
- [x] `.github/copilot-instructions.md` — updated with DSL Compiler sections 32–38 (this session)

---

## Current Focus

### DSL Builder (in progress)
The pipeline currently stops at `traverse_graph()`. The next stage is the **DSL Builder**: converting the ordered node list into Zigflow DSL task blocks.

What needs to be built per node type:

| Node Type | Builder Status | DSL Output |
|---|---|---|
| `START` | — | Emits nothing |
| `END` | — | Emits nothing |
| `INPUT` | Not started | `set` task mapping `$input.<field>` to `<store_as>` variable |
| `ACTION` | Not started | Activity call task with `operation` name and mapped inputs/output |
| `OUTPUT` | Not started | `set` task exposing named variables as workflow result |

**Key constraint:** The builder must remain a pure function per node type. No classes, no global state.

### Compile Output
`compile()` currently prints debug output only. It needs to return a structured Zigflow DSL dict and optionally serialize it to YAML.

---

## Next Steps (Ordered)

1. **Implement `build_input_node(node)`** — emits a `set` task block for each `inputs[]` entry
2. **Implement `build_action_node(node)`** — emits an activity call task block from `operation`, `inputs`, `output`
3. **Implement `build_output_node(node)`** — emits a `set` task block for each `outputs[]` entry
4. **Implement `build_dsl(traversal_order)`** — dispatcher that calls the correct builder per node type; skips `START` and `END`; returns a list of DSL task dicts
5. **Implement `compile()` return value** — return the full Zigflow DSL dict (with `document` and `do` blocks) instead of printing
6. **Add YAML serialization** — serialize the DSL dict to a YAML string using `yaml.dump`
7. **Validate with `workflow_1_output.json`** — run compiler end-to-end on the simple linear workflow and manually verify YAML output is valid Zigflow DSL
8. **Validate with `workflow_2_output.json`** — run compiler on the branching workflow; verify parallel branches are correctly represented
9. **Fuzz with workflow generator** — run the generator for N random workflows and verify `compile()` does not raise for any of them
10. **FastAPI wrapper (future)** — expose `compile()` behind `POST /api/v1/compile` accepting `{nodes, edges}` JSON body

---

## Out of Scope (Permanently for V1)

- `IF` node type
- `WAIT` node type
- `VARIABLE` node type
- `WORKFLOW` node type (sub-workflow)
- `PARALLEL` node type
- Template engine (Jinja2 or similar)
- Node / edge registry
- Cycle detection / validation errors
- REST API endpoint
- Execution bridge (triggering Zigflow + Temporal)
- UI layer (ReactFlow canvas)
