# 05 — POC Scope V1

## Purpose

This document defines the exact boundaries of the first POC of the generic Workflow → Zigflow DSL compiler. It exists to prevent scope creep and to give future contributors a clear line between what this POC is, and what it intentionally defers.

---

## What V1 Is

A **pure graph-to-DSL compiler**. Given a JSON graph document, it produces a valid Zigflow DSL YAML string. Nothing else.

```
JSON graph  →  compiler  →  Zigflow YAML
```

No network calls. No Temporal server connection. No execution of any kind.

---

## In Scope

### Node types
All eight frozen node types are in scope:

| Node type | In scope |
|---|---|
| START | yes |
| END | yes |
| ACTION | yes — all four subtypes (`call:http`, `call:grpc`, `run:script`, `run:shell`) |
| VARIABLE | yes — both operations (`set`, `export`) |
| WORKFLOW | yes |
| IF | yes |
| PARALLEL | yes — both modes (`compete: true`, `compete: false`) |
| WAIT | yes — both subtypes (`duration`, `signal`) |

### Graph shape
- Directed acyclic graphs (DAGs).
- Tree topology only (max one parent per node).
- Exactly one START, exactly one END.
- All nodes reachable from START.

### Compiler stages
- Stage 1: Graph parser.
- Stage 2: Validator (all 11 constraints listed in `04_compiler_pipeline_v1.md`).
- Stage 3: DSL Builder (DFS pre-order walk + registry dispatch + YAML serialization).

### Input format
JSON only. Schema defined in `02_graph_schema_v1.md`.

### Output format
Zigflow DSL YAML string. Optionally also serializable to JSON dict (same internal representation before `yaml.dump`).

### Error handling
Structured `ParseError`, `ValidationError`, `BuildError` objects with node IDs and messages. All validation errors collected before raising (not fail-on-first).

---

## Out of Scope for V1

### Execution
- No Temporal client connection.
- No workflow submission.
- No polling for results.
- No Zigflow worker startup.

### Runtime concerns
- No authentication.
- No secrets management.
- No environment variable injection at compile time.

### Storage and APIs
- No REST API or CLI entry point.
- No file system watching.
- No database or persistent storage.
- No caching of compiled outputs.

### Infrastructure
- No Docker image or compose file.
- No CI/CD pipeline.
- No deployment scripts.

### Node types not in V1
- LOOP — infinite or bounded loop constructs.
- AGENT — LLM/AI agent invocation.
- SIGNAL (as a node type) — distinct from WAIT[signal]. Named signal dispatch nodes are deferred.
- Any node type not in the frozen set of 8.

### Graph shapes not in V1
- Graphs with cycles (looping workflows).
- Graphs with merge points (a node with two or more incoming edges — i.e., diamond patterns).
- Disconnected subgraphs (multiple entry points or unreachable islands).
- Multiple START or multiple END nodes.

### LLM / AI integration
- No prompt generation from graph.
- No graph generation from natural language.
- No AI-assisted validation.

### UI
- No visual editor or preview.
- No React/browser component.

---

## V1 Assumptions

1. **Input is trusted but not guaranteed to be valid.** The validator exists precisely because input may be invalid. All structural errors are caught before generation.

2. **IF case-to-edge binding uses `sourceHandle`, not edge-array position.** Each edge from an IF node carries a `sourceHandle` value matching a `case.id` in `data.cases`. The builder resolves `then` references by looking up `sourceHandle` in `handle_map`. PARALLEL branch order is still determined by edge array order (branches are position-independent in Zigflow's `fork`).

3. **Task names are the primary key in the DSL `do` list.** Two nodes with the same resolved task name in the same workflow is a validation error.

4. **`data.name` is optional but preferred.** If absent, the node `id` is used as the task name. Node IDs are typically machine-generated; callers should always supply `data.name` for human-readable DSL.

5. **The `position` field in each node is UI metadata only.** The compiler reads it and ignores it. Node order in the DSL is determined solely by graph traversal.

6. **YAML output uses PyYAML.** `yaml.dump` with `default_flow_style=False` and `sort_keys=False`.

7. **The compiler is a pure function.** Same input always produces the same output. No randomness, no timestamps injected by the compiler.

8. **Graph metadata contains `name` and `description` only.** `taskQueue` and `workflowType` are not stored in the graph — they are runtime concerns injected by the deployment layer after compilation.

---

## V1 Limitations

| Limitation | Consequence | Future fix |
|---|---|---|
| Tree topology only | Cannot express merge/join patterns (e.g., two branches converging before END) | Generalise to DAG with explicit JOIN node |
| No cycle support | Cannot express loop/retry patterns in the graph | Add LOOP node type; emit `for` or recursive sub-workflow |
| No schema validation on `data` fields | Missing required fields caught only at builder time (BuildError) | Add per-type JSON Schema validation in Stage 2 |
| PARALLEL branch subtrees must not share nodes | No join point awareness; branches are compiled independently | Add JOIN node type; detect merge point during traversal |
| No `use` block support | Cannot reference named retry policies or authentication definitions | Add `use` section to graph schema; emit `use` in DSL header |
| Output is a string, not streamed | Entire YAML is built in memory | Acceptable for V1 graph sizes; streaming deferred |

---

## Non-Goals (Permanent)

These are intentionally outside the scope of this compiler at any version:

- **Being a workflow runtime.** The compiler produces DSL; Temporal/Zigflow executes it.
- **Being a graph editor.** Graph authoring is a UI concern, not a compiler concern.
- **Being a workflow registry.** Storing, versioning, or deploying compiled workflows is an ops concern.
- **Being an agent framework.** LLM orchestration is a separate layer above the DSL.

---

## Proposed Folder Structure

No code exists yet. This is the proposed layout for implementation.

```
poc-dsl-compiler/
├── docs/                  ← research documentation (this folder)
│   ├── 01_existing_poc_analysis.md
│   ├── 02_graph_schema_v1.md
│   ├── 03_node_mapping.md
│   ├── 04_compiler_pipeline_v1.md
│   └── 05_poc_scope.md    ← this file
│
├── models.py              ← Node, Edge, GraphModel, WorkflowMetadata dataclasses
├── validators.py          ← validate(graph_model) → None | raises ValidationError
├── builders.py            ← per-type DSL builder functions (build_action, build_if, …)
├── node_registry.py       ← { "ACTION": build_action, "IF": build_if, … }
└── compiler.py            ← compile(graph_json) → str; walk(); yaml.dump
```

### File rationale

| File | Rationale |
|---|---|
| `models.py` | All dataclasses in one place — shared by every other module |
| `validators.py` | Single responsibility: structural checks. No DSL knowledge. |
| `builders.py` | One function per node type — easy to add, easy to test in isolation |
| `node_registry.py` | Dispatch table only — adding a node type means adding one entry here and one function in `builders.py` |
| `compiler.py` | Top-level entry point; owns `compile()`, `walk()`, and `yaml.dump` assembly |

# Compiler Context — DSL Compiler Initiative

> **Status:** POC — active development
> **Last updated:** May 2026
> **Owner:** `poc-dsl-compiler/`

---

## 1. What This Is

The DSL Compiler is a **Visual Workflow → Zigflow DSL compiler**. It is not a Temporal workflow code generator. It does not execute workflows. It transforms a structured graph JSON produced by a UI workflow builder into a valid Zigflow DSL document that can be run by the Zigflow runtime on top of Temporal.

```
UI Workflow Builder
        ↓
  JSON Workflow Definition   ← compiler input
        ↓
      Compiler               ← this project
        ↓
  Zigflow DSL (JSON / YAML)  ← compiler output
        ↓
  Executed by Zigflow + Temporal
```

Temporal remains the **orchestration runtime only**. The compiler does not know about Workers, Task Queues, or Temporal Workflows. It only knows about graph nodes, edges, and their Zigflow DSL equivalents.

---

## 2. What This Is Not

| It is NOT | Why it matters |
|---|---|
| A Temporal workflow generator | Compiler output is Zigflow YAML, never Python workflow classes |
| A Zigflow worker | The compiler does not run or register workflows |
| A runtime execution engine | No network calls, no Temporal client, no subprocess |
| A template engine | V1 uses pure functions, no Jinja2 or template files |
| A class-based framework | All pipeline stages are module-level pure functions |

---

## 3. System Architecture

The compiler sits in **Tier 2** of a three-tier system defined in `Documents/workflow_builder_architecture.md`.

```
┌─────────────────────────────────────────────────────┐
│  Tier 1 — UI Layer (V2, not yet built)              │
│  ReactFlow canvas · node palette · config panel     │
│  Produces: WorkflowGraph JSON                       │
└────────────────────┬────────────────────────────────┘
                     │ POST /api/v1/workflows  (planned)
┌────────────────────▼────────────────────────────────┐
│  Tier 2 — Compiler (V1 POC — this project)          │
│  Graph → Node Map → Adjacency List → Graph Struct   │
│  → Traversal → DSL Builder → Zigflow YAML           │
└────────────────────┬────────────────────────────────┘
                     │ zigflow run (future)
┌────────────────────▼────────────────────────────────┐
│  Tier 3 — Execution Runtime                         │
│  Zigflow Worker · Temporal Server · Activity Workers│
└─────────────────────────────────────────────────────┘
```

V1 covers **Tier 2** only. Tier 1 (UI) is a V2 deliverable. Tier 3 integration (execution bridge) is out of scope for the current POC.

---

## 4. Compiler Pipeline

The pipeline is a sequential series of pure functions. Each stage has a single responsibility and produces a well-defined output consumed by the next stage. There is no shared mutable state between stages.

```
Workflow JSON  ({nodes, edges})
        │
        ▼
  generate_node_map(workflow)
        │  Returns: dict[node_id → node]
        ▼
  generate_adjacency_list(workflow)
        │  Returns: dict[source_id → [target_id, ...]]
        ▼
  find_entrypoint(node_map)
        │  Returns: str (node_id of the START node)
        ▼
  generate_graph_structure(entrypoint, node_map, adjacency, graph=None)
        │  Returns: nested dict representing the DAG
        │  Shared nodes (multi-parent) appear once via memoization
        ▼
  print_graph(graph)             ← debug only; not part of output
        │
        ▼
  traverse_graph(graph)
        │  Returns: ordered list of node dicts (DFS preorder)
        ▼
  DSL Builder (per node_type)
        │  Returns: Zigflow DSL dict / YAML string
        ▼
  Generated Zigflow DSL
```

**Implementation:** `poc-dsl-compiler/examples/workflow_compiler.py`

---

## 5. Frozen V1 Node Types

The following node types are the complete set for V1. Do not extend without updating the contract docs.

| Node Type | Emits DSL? | Purpose |
|---|---|---|
| `START` | No | Traversal entry point only |
| `END` | No | Traversal terminal only |
| `INPUT` | Yes — `set` task | Captures external input fields into named runtime variables |
| `ACTION` | Yes — activity call | Transforms runtime variables via a named operation |
| `OUTPUT` | Yes — `set` task | Exposes named runtime variables as the workflow result |

**Deferred (NOT in V1):** `IF`, `WAIT`, `VARIABLE`, `WORKFLOW`, `PARALLEL`

---

## 6. Design Constraints

These constraints are permanent for the V1 POC. They are not up for discussion during the POC phase.

| Constraint | Reason |
|---|---|
| No classes in compiler functions | Keeps the pipeline purely functional and easy to test |
| No templates in V1 | Templates add indirection; validate pure-function approach first |
| No registry in V1 | Registry adds abstraction; not needed until node types grow past 5 |
| Edges carry no business data | Routing logic in edges caused bugs in V0 (`poc-react-flow`). All data belongs in nodes. |
| Execution order from graph traversal only | Raw node array order is undefined; traversal is the only reliable source of order |
| Shared nodes must not be duplicated | DFS with a `visited` set ensures each node appears at most once in the output |
| Compiler is stateless | No global mutable state; every `compile()` call is independent |

---

## 7. V0 vs V1 — What Changed

**V0:** `poc-react-flow/` — a working prototype for a specific agent-routing workflow. Not generic. Edges carried business data (conditions). Node types were UI-specific (`agent-node`, `text-input`). No graph traversal — nodes were sorted by Y-axis position.

**V1:** `poc-dsl-compiler/` — a generic compiler. Edges are dumb (`{id, source, target}` only). Node types are semantic (`START`, `END`, `INPUT`, `ACTION`, `OUTPUT`). Execution order comes from DFS preorder graph traversal. Pure functions throughout.

The key reference from V0 that remains relevant: `poc-react-flow/node_conversion.py` — shows the pattern for builder functions that emit individual Zigflow DSL task blocks.

---

## 8. File Map

```
poc-dsl-compiler/
├── docs/
│   ├── 01_existing_poc_analysis.md     # Analysis of V0 (poc-react-flow)
│   ├── 02_graph_schema_v1.md           # Earlier graph schema draft (superseded by workflow_json_contract.md)
│   ├── 03_node_mapping.md              # Earlier node → DSL mapping (expanded node set)
│   ├── 04_compiler_pipeline_v1.md      # Earlier pipeline design (three-stage)
│   ├── 05_poc_scope.md                 # Earlier scope doc (wider than current frozen scope)
│   ├── compiler_context.md             # ← this file
│   ├── compiler_pipeline.md            # Frozen current pipeline (seven stages)
│   ├── compiler_progress.md            # Completed / current / next steps
│   ├── workflow_json_contract.md       # Frozen input JSON contract
│   └── testing_strategy.md            # Workflow generator and fuzz-testing approach
├── examples/
│   ├── workflow_compiler.py            # Core compiler implementation
│   ├── workflow_generator.py           # Random workflow generator
│   ├── workflow_1_output.json          # Sample: simple linear workflow
│   ├── workflow_1.md                   # Mermaid diagram for workflow_1
│   ├── workflow_2_output.json          # Sample: branching workflow
│   └── workflow_2.md                   # Mermaid diagram for workflow_2
└── templates/                          # DSL task block templates (future use; not active in V1)
```

> **Note:** Files `02_` through `05_` in `docs/` were written before the V1 scope was frozen to the current five node types. They contain useful background but may describe node types (`IF`, `PARALLEL`, `WAIT`, `VARIABLE`, `WORKFLOW`) that are **not** implemented in V1. The authoritative scope is in `workflow_json_contract.md` and this file.

# Testing Strategy — DSL Compiler V1

> **Status:** POC — active development
> **Last updated:** May 2026

---

## 1. Strategy Overview

The V1 testing strategy has two layers:

1. **Static sample inputs** — two hand-crafted `workflow_*.json` files covering the linear and branching cases
2. **Fuzz testing via workflow generator** — a random workflow generator that produces structurally valid graphs for stress-testing the pipeline

No formal test framework (pytest, unittest) is used in V1. Validation is manual inspection of compiler output. A formal test suite is a post-POC deliverable.

---

## 2. Static Sample Inputs

These files are committed to the repository and serve as the canonical test fixtures for the V1 compiler.

| File | Description | Graph Shape |
|---|---|---|
| `poc-dsl-compiler/examples/workflow_1_output.json` | Simple linear hello-world | `START → INPUT → ACTION → OUTPUT → END` |
| `poc-dsl-compiler/examples/workflow_2_output.json` | Branching with shared END | `START → INPUT → [ACTION_greet → OUTPUT_message, ACTION_calc_age → OUTPUT_age] → END` |

Companion Mermaid diagrams:
- `poc-dsl-compiler/examples/workflow_1.md`
- `poc-dsl-compiler/examples/workflow_2.md`

**How to run a static sample through the compiler:**

```python
import json
from workflow_compiler import compile

with open("workflow_1_output.json") as f:
    workflow = json.load(f)

compile(workflow)
```

---

## 3. Workflow Generator

**File:** `poc-dsl-compiler/examples/workflow_generator.py`

The workflow generator produces random, structurally valid workflow JSON documents. Its purpose is to exercise edge cases in the compiler pipeline that hand-crafted examples might miss — particularly shared-node handling, varying branch depths, and different node type sequences.

### How to Run

```bash
cd poc-dsl-compiler/examples
python workflow_generator.py
```

The script prompts for two parameters:
- **Total Nodes** — the approximate total number of nodes in the graph (including START and END)
- **Branches** — the number of parallel branches fanning out from the shared INPUT node

Output is written to `poc-dsl-compiler/examples/generated/`:
- `workflow.json` — the generated workflow (valid input for `compile()`)
- `workflow.md` — a Mermaid `graph TD` diagram for visual inspection

### Generated Graph Structure

Every generated workflow follows a fixed structural template:

```
START (N1)
  └─ INPUT (N2)   ← single shared INPUT node
       ├─ [branch 1 nodes: random INPUT / ACTION / OUTPUT chain]
       ├─ [branch 2 nodes: random INPUT / ACTION / OUTPUT chain]
       └─ [branch N nodes: ...]
         └─ END (last node)
```

All `OUTPUT` nodes are wired directly to the `END` node regardless of branch.

### Generator Functions

| Function | Signature | Purpose |
|---|---|---|
| `generate_input(node_id)` | `str → dict` | Creates a single INPUT node with one `field` / `store_as` pair |
| `generate_action(node_id, previous_node)` | `str, dict → dict` | Creates an ACTION node; reads `store_as` from the previous INPUT node or defaults to `"result"` |
| `generate_output(node_id)` | `str → dict` | Creates an OUTPUT node exposing a single `result_*` field |
| `generate_node(node_id, node_type, previous)` | `str, str, dict → dict` | Dispatcher; raises `Exception` on unsupported type |
| `generate_workflow(total_nodes, branches)` | `int, int → dict` | Produces the full `{nodes, edges}` JSON dict |
| `generate_mermaid(workflow)` | `dict → str` | Converts a workflow dict to a Mermaid `graph TD` string |
| `save_workflow(workflow, folder)` | `dict, str → None` | Writes `workflow.json` + `workflow.md` to the output folder |

### Supported Node Types in Generator

The generator randomly selects from:
- `INPUT`
- `ACTION`
- `OUTPUT`

`START` and `END` are always generated automatically — they are never part of the random selection.

### Known Limitations

- The generator does not guarantee that every branch ends with an `OUTPUT` node. Branches may end with `INPUT` or `ACTION` nodes, which means some generated workflows may have branches that never produce visible output.
- `total_nodes` is approximate. The exact count may differ slightly depending on branch sizing arithmetic.
- Node IDs are sequential integers (`N1`, `N2`, ...) — not UUIDs. This is intentional for readability.

---

## 4. Using the Generator for Fuzz Testing

After implementing the DSL Builder, fuzz-test the full pipeline with:

```python
from workflow_generator import generate_workflow
from workflow_compiler import compile

for i in range(100):
    workflow = generate_workflow(
        total_nodes=random.randint(5, 30),
        branches=random.randint(1, 5)
    )
    compile(workflow)   # must not raise
```

The goal is to confirm that `compile()` does not raise an unhandled exception for any structurally valid generated workflow.

---

## 5. Manual Validation Checklist

When running the compiler against a sample, verify the following in the output:

- [ ] `traverse_graph()` returns a list with no duplicate node IDs
- [ ] `START` appears first in the traversal order
- [ ] `END` appears last
- [ ] Shared nodes (nodes with two parents) appear exactly once in the list
- [ ] Branch node order is consistent with DFS preorder (left branch fully before right branch)
- [ ] DSL Builder output has one task block per `INPUT`, `ACTION`, and `OUTPUT` node
- [ ] No task block is emitted for `START` or `END`
- [ ] Zigflow DSL dict has valid `document` and `do` keys

---

## 6. Post-POC Test Plan (Not V1)

These are deferred until the DSL Builder is implemented:

- pytest unit tests for each pipeline stage function with known-good inputs and outputs
- Snapshot tests comparing `compile()` output YAML against reference YAML files
- Automated fuzz testing with a fixed random seed for reproducibility
- Schema validation of compiler output against the Zigflow DSL JSON Schema
- Integration test triggering `zigflow validate` on the compiled YAML
