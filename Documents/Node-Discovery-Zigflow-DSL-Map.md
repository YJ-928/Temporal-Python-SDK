# Workflow Builder — Node Discovery & Zigflow DSL Mapping (V1)

**Status:** R&D / Discovery
**Version:** 1.0
**Scope:** Visual Workflow Builder → Graph → Zigflow DSL → Temporal Runtime

---

# 1. Objective

Build a visual workflow system similar to:

- Lyzr Workflow Builder
- LangFlow
- n8n
- Node-RED
- Temporal Visual Workflows

Users should create workflows visually.

Users should:

```text
Drag nodes
↓

Connect nodes

↓

Configure properties

↓

Execute workflow
```

Users should NOT:

```text
Write YAML

Write JSON

Know Zigflow

Know Temporal
```

Backend responsibility:

```text
Graph

↓

Compiler

↓

Zigflow DSL

↓

Execution Runtime
```

This document exists ONLY to define:

```text
Zigflow Capability

↓

Visual Node
```

This document does NOT define:

- Compiler
- APIs
- Database
- Runtime
- Storage
- UI Implementation

---

# 2. Core Philosophy

---

## Rule 1 — User thinks in actions, not DSL

User should think:

```text
Fetch Data
```

NOT:

```yaml
call:
 http:
```

---

## Rule 2 — Multiple DSL primitives can become one node

Example:

```yaml
call:http

call:grpc

run:shell

run:script
```

↓

Single node:

```text
ACTION
```

---

## Rule 3 — Hide infrastructure concepts

These should not become nodes:

```yaml
document

use

retry

metadata

version
```

They belong in:

```text
Workflow Settings
```

---

## Rule 4 — Keep V1 intentionally small

V1 target:

```text
8 Nodes

5 Edge Types
```

---

# 3. Workflow Mental Model

User builds:

```text
START

↓

DO SOMETHING

↓

WAIT

↓

DECIDE

↓

END
```

System internally transforms:

```text
Graph

↓

Compiler

↓

Zigflow DSL

↓

Temporal Runtime
```

---

# 4. Node Categories

---

# Category A — Static Nodes

These exist only for graph structure.

They generate NO Zigflow DSL.

---

# START

## Purpose

Entry point of workflow.

Every workflow starts here.

---

## Zigflow Mapping

```text
None
```

---

## Inputs

```text
None
```

---

## Outputs

```text
DEFAULT
```

---

## Config

```json
{}
```

---

## Example

```text
START
↓
ACTION
```

---

# END

## Purpose

Terminates workflow.

---

## Zigflow Mapping

```text
None
```

---

## Inputs

```text
SUCCESS
ERROR
```

---

## Outputs

```text
None
```

---

## Config

```json
{}
```

---

## Example

```text
ACTION

↓

END
```

---

# Category B — Execution Nodes

These perform actual work.

---

# ACTION

## Purpose

Execute something.

---

## Combines Zigflow

```yaml
call:http

call:grpc

run:script

run:shell
```

---

## Config

```yaml
protocol:

method:

endpoint:

headers:

body:

command:

retry:

outputKey:
```

---

## Supported Protocols

| Protocol | Zigflow |
|----------|---------|
| http | call:http |
| grpc | call:grpc |
| script | run:script |
| shell | run:shell |

---

## Inputs

```text
INPUT
```

---

## Outputs

```text
SUCCESS

ERROR
```

---

## Example

```text
Fetch User

↓

Send Email

↓

Save Result
```

---

## Example Generated DSL

```yaml
- fetchUser:

    call: http

    with:

      method: GET

      endpoint: https://api.com
```

---

# VARIABLE

## Purpose

Create or update workflow data.

---

## Combines Zigflow

```yaml
set

export
```

---

## Config

```yaml
assignments:

export:
```

---

## Inputs

```text
INPUT
```

---

## Outputs

```text
SUCCESS
```

---

## Example

```text
Store User

↓

Set Status

↓

Transform Output
```

---

## Example Generated DSL

```yaml
- saveUser:

    set:

      name: user

    export:

      as: ...
```

---

# WORKFLOW

## Purpose

Run another workflow.

Supports composition.

---

## Combines Zigflow

```yaml
run workflow

child workflow

external workflow
```

---

## Config

```yaml
type:

workflowType:

taskQueue:

input:

outputKey:
```

---

## Inputs

```text
INPUT
```

---

## Outputs

```text
SUCCESS

ERROR
```

---

## Example

```text
Main Workflow

↓

Order Workflow

↓

Notification Workflow
```

---

## Example Generated DSL

```yaml
- executeOrder:

    run:

      workflow:
```

---

# Category C — Control Flow Nodes

These control execution.

---

# IF

## Purpose

Branch execution.

---

## Combines Zigflow

```yaml
switch
```

---

## Config

```yaml
condition:
```

---

## Inputs

```text
INPUT
```

---

## Outputs

```text
TRUE

FALSE
```

---

## Example

```text
Payment Success?

↙       ↘

YES     NO
```

---

## Example Generated DSL

```yaml
switch:

- when:

- then:
```

---

# PARALLEL

## Purpose

Run multiple branches simultaneously.

---

## Combines Zigflow

```yaml
fork

parallel

compete
```

---

## Config

```yaml
compete:

outputKey:
```

---

## Modes

### ALL COMPLETE

```yaml
compete: false
```

---

### FIRST WINS

```yaml
compete: true
```

---

## Inputs

```text
INPUT
```

---

## Outputs

```text
SUCCESS

ERROR
```

---

## Example

```text
PARALLEL

↙ ↓ ↘

A B C
```

---

## Example Generated DSL

```yaml
fork:

 compete:
```

---

# WAIT

## Purpose

Pause execution.

---

## Combines Zigflow

```yaml
wait

listen

signal
```

---

## Modes

---

### TIMER

```yaml
wait:
```

---

### SIGNAL

```yaml
listen:
```

---

## Config

```yaml
mode:

duration:

signalName:

timeout:

outputKey:
```

---

## Inputs

```text
INPUT
```

---

## Outputs

```text
SUCCESS

ERROR
```

---

## Example

```text
WAIT 30 min

↓

CONTINUE
```

---

## Example Generated DSL

Timer:

```yaml
wait:
 minutes:30
```

Signal:

```yaml
listen:
 to:
```

---

# 5. Hidden Workflow Concepts (NOT Nodes)

These remain in settings.

| Zigflow | UI Location |
|----------|------------|
| document | Workflow Settings |
| metadata | Workflow Settings |
| retries | Workflow Settings |
| version | Workflow Settings |
| namespace | Workflow Settings |
| taskQueue | Workflow Settings |

---

# 6. Edge Model (V1)

Edges represent simple directional connections between nodes.

Edges do not contain execution logic.

Workflow behavior is determined by:

```text
Node Type
+
Node Configuration
+
Connected Outputs
```

Edges only describe:

```text
Where execution goes next
```

---

## Edge Structure

```json
{
  "id": "edge_1",

  "source": "node_1",

  "sourceHandle": "output",

  "target": "node_2",

  "targetHandle": "input"
}
```

---

## Fields

| Field | Purpose |
|---|---|
| id | Unique edge identifier |
| source | Source node ID |
| sourceHandle | Output handle on source node |
| target | Destination node ID |
| targetHandle | Input handle on target node |

---

## Examples

### Normal Flow

```text
START

↓

ACTION

↓

END
```

```json
{
  "source": "start",
  "target": "action"
}
```

---

### Conditional Flow

```text
IF

↙     ↘

TRUE  FALSE
```

```json
[
  {
    "source": "if_1",
    "sourceHandle": "true",
    "target": "approve"
  },

  {
    "source": "if_1",
    "sourceHandle": "false",
    "target": "reject"
  }
]
```

---

### Action Result Flow

```text
ACTION

success
↓

NEXT

error
↓

END
```

```json
[
  {
    "source": "action_1",
    "sourceHandle": "success",
    "target": "next"
  },

  {
    "source": "action_1",
    "sourceHandle": "error",
    "target": "end"
  }
]
```

---

## V1 Rules

```text
Edges are generic.

Edges are directional.

Edges contain no business logic.

Node handles define execution behavior.
```

---

# 7. Zigflow → Node Mapping

| Zigflow DSL | Node |
|------------|------|
| call:http | ACTION |
| call:grpc | ACTION |
| run:script | ACTION |
| run:shell | ACTION |
| set | VARIABLE |
| export | VARIABLE |
| switch | IF |
| fork | PARALLEL |
| wait | WAIT |
| listen | WAIT |
| workflow | WORKFLOW |

---

# 8. Example Workflows

---

## Example 1 — Hello User

Visual:

```text
START

↓

ACTION
(Get Name)

↓

VARIABLE
(Store Name)

↓

ACTION
(Say Hello)

↓

END
```

Internal Meaning:

```text
Input

↓

Store

↓

Output
```

---

## Example 2 — Approval Workflow

Visual:

```text
START

↓

ACTION
(Create Request)

↓

WAIT
(signal)

↓

IF

↙       ↘

Approve Reject

↓

END
```

---

## Example 3 — Parallel Fetch

Visual:

```text
START

↓

PARALLEL

↙ ↓ ↘

Users Orders Inventory

↓

END
```

---

## Example 4 — Child Workflow

Visual:

```text
START

↓

WORKFLOW
(Process Order)

↓

WORKFLOW
(Send Notification)

↓

END
```

---

# 9. V1 Scope

Included:

```text
START

END

ACTION

VARIABLE

IF

PARALLEL

WAIT

WORKFLOW
```

---

Edge Types:

```text
DEFAULT

SUCCESS

ERROR

TRUE

FALSE
```

---

Excluded:

```text
LOOP

AI_AGENT

HUMAN_APPROVAL

MCP

IMPORT DSL

EXPORT GRAPH

UI
```

---

# 10. Open Questions

These require further Zigflow validation.

| Question | Impact |
|----------|--------|
| Exact switch DSL | IF |
| Exact fork DSL | PARALLEL |
| Child workflow DSL | WORKFLOW |
| Signal timeout behavior | WAIT |
| Retry mapping | ACTION |

---

# 11. Deliverables After This Document

Next documents only:

```text
graph_schema_v1.md
```

Then:

```text
compiler_poc.md
```

DO NOT proceed to:

```text
API

Database

Execution

UI
```

until Node Discovery is frozen.

---

END
