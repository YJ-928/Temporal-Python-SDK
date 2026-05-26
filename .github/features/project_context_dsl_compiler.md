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
"node_map":{},
"adjacency":{},
"graph":{},
"traversal":[]
}
```

Compiler NEVER emits DSL.

Compiler owns graph understanding.

Traversal:

DFS preorder.

Shared nodes deduplicated.

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

Generator receives traversal.

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

INPUT → set

ACTION → call:http

WAIT → wait

OUTPUT → set

END → None

Builders never:

* traverse
* validate
* execute
* import compiler

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

# Implemented Nodes

V1 Complete:

START

INPUT

ACTION

WAIT

OUTPUT

END

---

# Deferred Nodes

V2:

IF

PARALLEL

VARIABLE

WORKFLOW

---

# WAIT Design

Single WAIT node.

Modes:

duration

signal

event

Current:

duration implemented.

Future:

signal

event

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

Workflow JSON

↓

Compiler

↓

Traversal

↓

DSL

↓

Validation

Complete.

Next milestone:

WAIT variants

↓

IF

↓

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
