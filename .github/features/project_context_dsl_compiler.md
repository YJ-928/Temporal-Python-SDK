# Zigflow DSL Compiler — Project Context (Working Memory)

Status: Source of Truth
Project: `poc-dsl-compiler`
Architecture Version: V1
Last Verified: 2026-05

---

# Purpose

This document exists to preserve the architecture decisions, mental model, and current implementation state of the Zigflow DSL Compiler POC.

Future sessions must read this before modifying:

* compiler.py
* dsl_generator.py
* builders/
* workflow_generator.py
* templates/
* output/
* workflow JSON schema

This document explains:

* what we are building
* why it is built this way
* what has already been solved
* what remains

---

# Project Goal

Build a reusable compiler that converts a visual workflow JSON into a valid Zigflow DSL document.

Target:

```text
UI Workflow JSON
↓

Compiler

↓

Graph

↓

Traversal

↓

DSL Generator

↓

DSL JSON

↓

zigflow validate
```

Long-term goal:

```text
UI
↓

Workflow Engine

↓

Zigflow DSL

↓

Runtime

↓

External Execution
```

Compiler must remain independent from runtime.

---

# Core Philosophy

This project is NOT building a workflow runtime.

This project IS building:

```text
Visual Workflow

↓

Compiler

↓

Portable DSL
```

Execution belongs outside.

Compiler generates.

Runtime executes.

---

# Architecture

## Layer 1 — UI

Produces:

```json
{
  "nodes": [],
  "edges": []
}
```

Rules:

* node order irrelevant
* edges define execution
* JSON is source of truth
* UI never emits DSL

---

## Layer 2 — Compiler

File:

```text
compiler.py
```

Responsibilities:

* generate_node_map()
* generate_adjaceny_list()
* find_entrypoint()
* generate_graph_structure()
* traverse_graph()

Output:

```python
{
  "node_map": {},
  "adjacency": {},   # {source_id: [(target_id, control), ...]}; control=None for non-IF edges
  "graph":    {},
  "traversal": [],   # list[TraversalEntry] — see Phase A/B boundary below
  "builder_context": {}  # deprecated; formerly {adjacency, node_map}; now always empty dict
}
```

TraversalEntry shape (from `utils/traversal_types.py`):

```python
class TraversalEntry(TypedDict):
    node_id:               str
    node_type:             str
    node:                  dict          # READ-ONLY — shared reference from memoised DAG
    is_terminal:           bool          # True when any direct successor is END
    successors:            list[str]     # direct successor node IDs
    incoming_edge_control: dict | None   # control dict from parent edge; None for START
    branch_map:            BranchMap | None  # IF nodes only; pre-computed by traverse_graph()
```

## Phase A / Phase B Boundary

| Concern | Owner | File |
|---|---|---|
| node_map, adjacency, graph structure | Phase A | `compiler.py` |
| DFS traversal, is_terminal, branch_map, task name resolution | Phase A | `compiler.py` |
| Builder dispatch, DSL fragment collection | Phase B | `dsl_generator.py` |
| DSL fragment construction | Phase B | `builders/*.py` |
| Document header assembly | Phase B | `dsl_boilerplate_builder.py` |

The ONLY thing that crosses the Phase A/B boundary is `list[TraversalEntry]`. No builder reads adjacency, node_map, or graph internals.

Compiler NEVER emits DSL.

Compiler owns graph understanding.

Traversal: DFS preorder. Shared nodes deduplicated.

---

## Layer 3 — DSL Generator

File:

```text
dsl_generator.py
```

Responsibilities:

* generate_dsl_boilerplate()
* dispatch builders
* assemble document
* serialize output

Generator NEVER traverses graph.

Generator receives `list[TraversalEntry]` from Phase A.

Generator passes `traversal_entry=entry` to each builder call so builders can read `is_terminal`, `branch_map`, etc.

Generator is assembler.

---

## Layer 4 — Builders

Directory:

```text
builders/
```

Responsibilities:

Node

↓

DSL fragment

Only.

Builders:

START → None

INPUT → set (reads `$input.*`, exports to `$context` via `export.as`)

ACTION → call:http (reads inputs from `$context`, exports output to `$context`)

WAIT → wait (duration mode) or listen (listen mode)

OUTPUT → set

IF → switch (case/when/then + default/then); routing via `traversal_entry["branch_map"]`

END → None

All builders have signature:

```python
def build_<type>(node: dict, *, traversal_entry=None, compiler_context=None) -> dict | None
```

`compiler_context` is deprecated. Always `None` or `{}`. Not read by any builder.

`then: end` injection: each builder (except terminal_builder and if_builder) checks `traversal_entry["is_terminal"]` and adds `"then": "end"` to its fragment. This is the builder's responsibility.

Builders never:

* traverse
* validate
* execute
* import compiler
* read adjacency or node_map

---

# Templates

Templates are documentation.

Templates are:

NOT imported

NOT executed

NOT loaded

Used only for:

* examples
* builder reference
* future nodes

Builder output is source of truth.

---

# Runtime Model

Current ACTION strategy:

```text
ACTION

↓

HTTP
```

Compiler emits:

```json
{
"call":"http"
}
```

Runtime decides:

* HTTP
* retries
* signals
* execution

Compiler does not know runtime.

Current POC:

```text
localhost/{operation}
```

Future:

```text
service registry
```

---

# Workflow Generator

File:

```text
workflow_generator.py
```

Purpose:

Generate random workflows.

Outputs:

* workflow JSON
* Mermaid graph

Generator:

Does not compile.

Compiler consumes.

Current:

Difficulty-based generation.

---

# $context Persistence

INPUT and ACTION builders export captured variables into Zigflow `$context` so they survive across subsequent `call: http` tasks that replace the flowing data context.

* INPUT: `export.as: ${ $context + {var1: .var1, var2: .var2} }`
* ACTION body reads: `${ $context.ctx_var }` (not `${ .<var> }`)
* ACTION: `export.as: ${ $context + {output_var: .output_var} }`

This ensures chained ACTION nodes and parallel branches can always access previously captured variables regardless of how many prior HTTP tasks have replaced the flowing data.

---

# Known Limitations (V1)

| Limitation | Detail |
|---|---|
| Reconvergence (JOIN/diamond) | DFS visits a shared convergence node from the first branch only. No JOIN semantics. Produces incorrect DSL for diamond patterns. |
| PARALLEL | No `fork` task generation. Deferred to V2. |
| LOOP/cycle | No cycle detection beyond `visited` set deduplication. Infinite loops would cycle in DFS. |
| `builder_context` | Deprecated. Retained as `{}`. No builder reads it. |
| ACTION host | Hardcoded to `http://localhost:8080/{operation}`. No service registry. |
| ACTION method | Always `post` in V1. |
| IF data field | Optional. Simple IF nodes have no `data`. Condition is a root-level key. |

---

# Implemented Nodes

V1 Complete:

START

INPUT

ACTION

WAIT

OUTPUT

IF

END

---

# IF Node Schema

`condition` is a root-level key on IF nodes — same level as `id`, `type`, `data`:

```json
{ "id": "N3", "type": "IF", "condition": { "left": "user_email", "operator": "!=", "right": "" } }
```

For nested IF where a child needs parent-scoped values, `data` carries those values:

```json
{ "id": "N4", "type": "IF", "condition": { "left": "email_verified", "operator": "==", "right": true }, "data": { "parent_field": "..." } }
```

`data` is optional — omitted for simple IF nodes. `condition` is always required.

Expression building: `builders/condition_builder.py → build_condition_expression(condition)` → `'${ .user_email != "" }'`

This utility is shared — any future node type that evaluates a condition imports from `condition_builder`, not from `if_builder`.

---

# Deferred Nodes

V2:

PARALLEL

VARIABLE

WORKFLOW

---

# WAIT Design

Single WAIT node.

Modes:

duration

listen

Both implemented.

WAIT changes DSL only.

Not graph.

---

# Current Compiler Flow

```text
generate_node_map()

↓

generate_adjaceny_list()

↓

find_entrypoint()

↓

generate_graph_structure()

↓

traverse_graph()

↓

generate_dsl()

↓

save_dsl()

↓

zigflow validate
```

Current result:

PASS

---

# Rules

Do not introduce:

* classes
* registries
* factories
* runtime execution
* graph logic inside generator

Preserve:

pure functions

dispatch table

builder ownership

compiler ownership

---

# Node Addition Checklist

builder

↓

dispatch

↓

template

↓

workflow_generator

↓

input example

↓

validation

↓

current_state

↓

decision_log

↓

copilot instructions

↓

feature docs

---

# Decision Summary

Accepted:

Pure functions

Dispatch dictionary

Templates as docs

Compiler/Generator separation

HTTP action model

Rejected:

Registry pattern

Runtime execution

Template loading

Compiler-generated execution

---

# Current Milestone

All 11 difficulty levels compiled and validated:

```
python3 validate_outputs.py   →   11/11 PASS
```

Next:

PARALLEL

↓

WORKFLOW

---

# Priority Order

Code

>

Feature Docs

>

Copilot Instructions

If conflict occurs:

implementation wins.

Update docs later.

---

# Session Resume Prompt

If continuing in a future session:

Read:

.github/features/project_context_dsl_compiler.md

.github/features/current_state.md

.github/features/decision_log.md

.github/copilot-instructions.md

Then continue implementation without redesign.
