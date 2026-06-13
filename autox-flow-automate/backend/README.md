# FlowAutomate Backend — by AutoX

Visual Workflow → Zigflow DSL Compiler, Runtime Bootstrap, and Execution Engine

---

## Overview

FlowAutomate Backend is the AutoX workflow automation service responsible for transforming visual workflow definitions into executable Zigflow DSL and orchestrating their execution on Temporal.

The project does **not** implement its own workflow runtime.

Instead, it uses:

* Zigflow as the workflow runtime
* Temporal as the execution platform
* Python only for compilation, validation, API orchestration, and runtime bootstrap

---

## System Architecture

```text
Frontend Workflow Builder
            │
            ▼
      Workflow JSON
            │
            ▼
      Compiler Engine
            │
            ▼
       Zigflow DSL
            │
            ▼
      Zigflow Runtime
            │
            ▼
      Temporal Cluster
            │
            ▼
     Workflow Execution
```

---

## Core Responsibilities

### Compiler

Transforms frontend workflow graphs into valid Zigflow DSL.

Supported nodes:

* START
* END
* INPUT
* OUTPUT
* ACTION
* AGENT
* IF

Output:

```json
{
  "document": {},
  "do": []
}
```

compatible with Zigflow CLI validation and execution.

---

### API Layer

Provides endpoints used by the frontend workflow builder.

Responsibilities:

* Accept workflow JSON
* Validate payload
* Compile workflow
* Persist generated DSL
* Return compilation results

---

### Runtime Bootstrap

Provides infrastructure scripts for local development.

Responsibilities:

* Start Temporal
* Start Zigflow workers
* Start demo agents
* Validate generated DSL

Runtime execution itself is delegated to Zigflow.

---

## Repository Structure

```text
src/backend/

app/
├── api/
├── builders/
├── compiler/
├── schemas/
├── services/
├── agents/
└── compiler_main.py

resources/
├── compiled/
├── agent_data/
└── runtime_data/

scripts/
├── start.sh
├── start_agents.sh
├── start_temporal.sh
└── start_workers.sh

docs/
```

---

## Compilation Pipeline

### Phase A – Graph Analysis

Input:

```text
Nodes + Edges
```

Produces:

```text
Traversal Plan
```

Responsibilities:

* Node indexing
* Graph traversal
* Branch resolution
* Execution ordering

---

### Phase B – DSL Generation

Input:

```text
Traversal Plan
```

Produces:

```text
Zigflow DSL
```

Responsibilities:

* Builder dispatch
* DSL fragment generation
* Workflow assembly

---

## Local Development

### Start Everything

```bash
./scripts/start.sh
```

This starts:

* Temporal Dev Server
* Zigflow Workers
* Demo Agents

---

### Compile Workflow

```bash
POST /api/v1/workflows/compile
```

Input:

```json
{
  "nodes": [],
  "edges": []
}
```

Output:

```json
{
  "success": true,
  "dsl_path": "...",
  "workflow_type": "...",
  "task_queue": "..."
}
```

---

## Zigflow Integration

Compiler output is validated using:

```bash
zigflow validate workflow.json
```

Workers are started using:

```bash
zigflow run -f workflow.json
```

Workflow execution is performed through Temporal.

The backend does not implement a custom runtime engine.

---

## Demo Agents

Available demo services:

| Agent                 | Port  |
| --------------------- | ----- |
| Weather Agent         | 11000 |
| Email Validator Agent | 11001 |
| Email Sender Agent    | 11002 |

These agents exist only to demonstrate workflow integration.

They are not part of the compiler itself.

---

## Current Scope

Implemented:

* Workflow Compiler
* Zigflow DSL Generation
* API Integration
* Demo Agent Infrastructure
* Temporal Bootstrap Scripts

Deferred:

* Parallel Nodes
* Wait Nodes
* Advanced Runtime Orchestration
* Production Worker Management

---

## Technology Stack

Backend:

* Python
* FastAPI
* Pydantic

Workflow:

* Zigflow

Execution:

* Temporal

Infrastructure:

* Docker
* Bash

---

## Design Principles

### Compiler First

The compiler is the primary product.

### Runtime Reuse

Do not rebuild workflow execution engines already provided by Zigflow.

### Temporal Native

Workflow execution should always run through Temporal.

### Separation of Concerns

Compiler:

```text
Workflow JSON
        ↓
Zigflow DSL
```

Runtime:

```text
Zigflow DSL
        ↓
Temporal Execution
```

---

## Documentation

See:

```text
docs/
├── COMPILER_ARCHITECTURE.md
├── ZIGFLOW_RUNTIME_VALIDATION_REPORT.md
├── AGENTS.md
├── API_REFERENCE.md
└── DEVELOPMENT_GUIDE.md
```

---

## Project Status

Current Focus:

```text
Frontend JSON
        ↓
Compiler
        ↓
Valid Zigflow DSL
```

Runtime execution integration with Zigflow and Temporal is the next milestone.

The compiler remains the primary production component of this repository.
