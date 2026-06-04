# AUTOX 2.0 — Project Context

## Project

AutoX 2.0

A visual workflow automation platform.

Users create workflows through a drag-and-drop visual editor.

The platform compiles workflows into Zigflow DSL.

The generated Zigflow DSL is then executed by Zigflow Runtime using Temporal.

---

## Core Goal

Transform:

Visual Workflow Builder

↓

Workflow JSON

↓

Compiler

↓

Zigflow DSL

↓

Temporal Execution

The compiler is the core intellectual asset of the project.

---

## Current Architecture

Frontend:

* React
* ReactFlow

Backend:

* FastAPI
* Python

Workflow Runtime:

* Zigflow
* Temporal

---

## Compiler Philosophy

Compiler generates DSL only.

Compiler never executes workflows.

Compiler never becomes a runtime.

Compiler remains stateless.

---

## Current Supported Nodes

START

END

INPUT

OUTPUT

ACTION

AGENT

IF

---

## Current Compiler Design

Workflow JSON

↓

Graph Compilation

↓

TraversalEntry[]

↓

DSL Generation

↓

Zigflow DSL

Graph compilation and DSL generation are intentionally separated.

Builders are pure functions.

TraversalEntry is the boundary between graph analysis and DSL generation.

---

## Current Status

Working POC.

Compiler foundation exists.

IF support exists.

Agent support exists.

Basic DSL generation exists.

Swagger APIs exist.

Workflow Builder exists.

---

## Known Problems

1. Frontend and backend workflow schemas have drifted.

Examples:

* operation vs operator
* branch1/branch2 vs true/false
* InputField ids
* OutputField ids

2. Workflow contract is not yet frozen.

3. Validation layer needs review.

4. Graph traversal needs verification against latest frontend output.

5. End-to-end compile path needs stabilization.

---

## Future Nodes

WAIT

PARALLEL

JOIN

LOOP

VARIABLE

SUBFLOW

These are intentionally deferred.

Do not implement unless required.

---

## Non-Negotiable Rules

1. Compiler never executes workflows.

2. Graph logic stays in graph compilation.

3. Builders remain pure.

4. TraversalEntry remains compiler boundary.

5. Runtime concerns stay in Zigflow.

6. Prefer adapting compiler to frontend contract rather than forcing frontend to match compiler internals.
