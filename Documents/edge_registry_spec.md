# Edge Registry Specification

> **Status:** R&D / Design Phase
> **Purpose:** Defines the catalog of all 6 V1 edge types, their semantic meanings, valid source/target node pairings, handle resolution rules, and validation constraints.

---

## 1. What Is the Edge Registry?

The Edge Registry describes the valid types of connections between nodes. Like the Node Registry, it is data-driven — each edge type is defined in a YAML file in `registry/edge_definitions/`. The compiler reads these at startup to:

- **Validate** connections (is this edge type allowed between these node types?)
- **Route** the IR builder (does this edge create a branch? a fallback? a loop?)
- **Resolve handles** (does this edge's `source_handle` match an expected output handle?)

**Key semantic point:** `edge_type` is not decorative. It tells the compiler *what the connection means*, not just *that two nodes are connected*. The generator uses edge type to decide how to nest tasks in the output DSL.

---

## 2. Edge Definition YAML Schema

```yaml
# Canonical schema for edge_definitions/*.yaml

type: STRING              # EdgeType enum value (uppercase)
description: STRING       # Human-readable description

allowed_source_types:     # node types that can be the source
  - NodeType
  - NodeType

allowed_target_types:     # node types that can be the target
  - NodeType
  - NodeType

expected_source_handle:   # if set, the edge must use this source handle id
  STRING | null

role:                     # semantic role in the IR
  SEQUENTIAL              # connects two tasks in order
  BRANCH_TRUE             # enters the "true" path of a conditional
  BRANCH_FALSE            # enters the "false" path of a conditional
  PARALLEL_BRANCH         # enters one branch of a concurrent fork
  ERROR_FALLBACK          # enters an error-handling path
  LOOP_BACK               # connects the end of a loop body back to a loop node
```

---

## 3. V1 Edge Catalog (6 Types)

### 3.1 DEFAULT

```
Meaning      Standard sequential connection — the next step after this node
Role         SEQUENTIAL
Source       START, or any node type (as a fallback)
Target       Any node type
Handle       Unspecified — connects any output to any input
```

**When to use:** START → first node (START has no protocol-specific output, so DEFAULT is appropriate). Also a fallback for VARIABLE → next step and WAIT (timer) → next step where no success/error distinction is needed.

**Constraint:** Only one DEFAULT edge may originate from a given source node, unless the source is PARALLEL (where multi-DEFAULT is ambiguous and invalid). IF nodes must not use DEFAULT — they must use TRUE/FALSE.

---

### 3.2 SUCCESS

```
Meaning      Previous step completed successfully; proceed with the happy path
Role         SEQUENTIAL
Source       ACTION, VARIABLE, WAIT, WORKFLOW, PARALLEL
Target       Any node type
Handle       source_handle: "success"
```

**When to use:** After an ACTION, WAIT, or WORKFLOW node when the step succeeded. Also used as the branch connector for PARALLEL — each outbound branch from a PARALLEL node uses SUCCESS.

**Relationship to DEFAULT:** SUCCESS and DEFAULT both represent sequential flow. The distinction is:
- DEFAULT: no success/error distinction available or needed (e.g., after START)
- SUCCESS: the source node has both success and error outputs; this edge takes the success path

**Compiler behavior:** A SUCCESS edge from a PARALLEL node signals a parallel branch start, not sequential flow. The compiler identifies this by checking if the source is PARALLEL.

---

### 3.3 ERROR

```
Meaning      Previous step failed; route to error-handling path
Role         ERROR_FALLBACK
Source       ACTION, WAIT, WORKFLOW, PARALLEL
Target       Any node type (typically VARIABLE, another ACTION, or END)
Handle       source_handle: "error"
```

**When to use:** Explicit error routing. If an ACTION fails (after exhausting Zigflow retries), the ERROR edge path executes.

**V1 limitation:** As discussed in `node_registry_spec.md`, V1 may not support ERROR edges by wrapping tasks in `try`/`catch`. The error path may be advisory only — the workflow fails at the Temporal level rather than routing to the error subtree. This is a significant V1 scope decision.

**If ERROR edges are advisory in V1:**
- The compiler emits a warning: `WARNING: ERROR edge from {node_id} ignored in V1 — errors will propagate to Temporal as workflow failure`
- The ERROR subtree nodes and edges are present in the graph but generate no DSL output

**If ERROR edges are supported in V1 (Option A from node_registry_spec.md):**
- The generator wraps the source task in `try: [...] catch: {do: [error_subtree_tasks]}`
- The IR builder must recognize that the error subtree belongs inside the catch block

---

### 3.4 TRUE

```
Meaning      Condition evaluated to true; take this branch
Role         BRANCH_TRUE
Source       IF only
Target       Any node type
Handle       source_handle: "true"
```

**Constraint:** Exactly one TRUE edge must originate from each IF node. The validator enforces this with `MISSING_BRANCH` or `MULTIPLE_BRANCH` errors.

**Compiler behavior:** The IR builder identifies the TRUE edge from an IF node and recursively walks the true-path subgraph. The generator renders the true-path tasks inside the `when: {condition}` case of the `switch` task.

---

### 3.5 FALSE

```
Meaning      Condition evaluated to false; take this branch (default case)
Role         BRANCH_FALSE
Source       IF only
Target       Any node type
Handle       source_handle: "false"
```

**Constraint:** Exactly one FALSE edge must originate from each IF node.

**Compiler behavior:** The false path becomes the default case in the Zigflow `switch` task — the case without a `when` condition.

---

### 3.6 LOOP

```
Meaning      Loop back-edge — connects the last step of a loop body to a predecessor node
Role         LOOP_BACK
Source       Any node type (the last step of a loop body)
Target       Any node type (a predecessor that was already visited in the graph traversal)
Handle       Unspecified
```

**V1 status:** LOOP back-edges are supported at the graph level (the validator must not reject them as invalid cycles). However, the IR builder's behavior on LOOP edges is an open design question.

**V1 design question:** LOOP edges could compile to:
1. A Zigflow `for` task — requires the PARALLEL/LOOP node type (V2)
2. A Temporal `continue_as_new` call — requires the WORKFLOW node with `continue_as_new` config
3. A Zigflow inline recursion pattern — not supported in Zigflow DSL
4. Simply not supported in V1 — a LOOP edge causes a `LOOP_NOT_SUPPORTED_V1` error

**V1 recommendation:** LOOP edges are parsed and stored in the graph (schema supports them). Attempting to compile a graph with a LOOP edge in V1 raises `LOOP_NOT_SUPPORTED_V1` with a message explaining V2 plans. This prevents silent incorrect output.

---

## 4. Connection Validity Matrix

The matrix below defines which edge types are valid between node type pairs. "✓" = valid, "✗" = invalid, "-" = not applicable (node has no outbound edges from that type).

| Source \ Target | START | END | ACTION | VARIABLE | IF | PARALLEL | WAIT | WORKFLOW |
|---|---|---|---|---|---|---|---|---|
| **START** (DEFAULT only) | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **END** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **ACTION** (SUCCESS/ERROR) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **VARIABLE** (SUCCESS/DEFAULT) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **IF** (TRUE/FALSE only) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **PARALLEL** (SUCCESS branches/ERROR) | ✗ | ✓ | ✓ | ✓ | ✓ | ✗* | ✓ | ✓ |
| **WAIT** (SUCCESS/ERROR) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **WORKFLOW** (SUCCESS/ERROR) | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

*`PARALLEL → PARALLEL` as a branch target: not recommended in V1. Nested forks are valid in Zigflow but introduce IR complexity. V1 restriction: parallel branches cannot contain another PARALLEL node.

### Edge type allowed per source

| Source | Allowed edge types |
|---|---|
| START | DEFAULT only |
| END | None (no outbound edges) |
| ACTION | SUCCESS, ERROR |
| VARIABLE | SUCCESS, DEFAULT |
| IF | TRUE, FALSE (exactly one of each) |
| PARALLEL | SUCCESS (per branch), ERROR |
| WAIT | SUCCESS, ERROR |
| WORKFLOW | SUCCESS, ERROR |

---

## 5. Handle Resolution

### What is handle resolution?

Each edge has optional `source_handle` and `target_handle` fields referencing handle IDs on the source and target nodes respectively. Handle resolution is the process of:

1. Looking up the source node's `outputs` array
2. Confirming that `source_handle` matches an output handle ID
3. Looking up the target node's `inputs` array
4. Confirming that `target_handle` matches an input handle ID

### Canonical handle IDs per node type

| Node | Output handles |
|---|---|
| START | `output` |
| ACTION | `success`, `error` |
| VARIABLE | `success` |
| IF | `true`, `false` |
| PARALLEL | `success` (×N for branches), `error` |
| WAIT | `success`, `error` |
| WORKFLOW | `success`, `error` |

| Node | Input handles |
|---|---|
| END | `input` |
| ACTION | `input` |
| VARIABLE | `input` |
| IF | `input` |
| PARALLEL | `input` |
| WAIT | `input` |
| WORKFLOW | `input` |

**When `source_handle` is omitted:** The normalizer infers it from `edge_type`:
- `DEFAULT` → no handle inference (accepts any output)
- `SUCCESS` → infers `source_handle: "success"`
- `ERROR` → infers `source_handle: "error"`
- `TRUE` → infers `source_handle: "true"`
- `FALSE` → infers `source_handle: "false"`

This means the UI does not need to explicitly set handle IDs in every edge — `edge_type` alone is sufficient for the normalizer to resolve handles.

---

## 6. Loop Edge vs Cycle Detection

The validator must distinguish **valid LOOP back-edges** from **invalid cycles**.

**Rule:**
- An edge with `edge_type: LOOP` that points to a predecessor is a valid back-edge. The cycle detector skips this edge when checking for cycles.
- Any cycle that does NOT use a LOOP-typed edge is an invalid cycle and raises `CYCLE_DETECTED`.

**Algorithm:**

```
1. Build adjacency list from all edges WHERE edge_type != LOOP
2. Run topological sort on the non-LOOP graph
3. If topological sort fails (cycle) → raise CYCLE_DETECTED
4. The topological order is valid for IR building
5. LOOP edges are tracked separately as back-edge annotations on IR tasks
```

This means LOOP edges are structurally present in the graph but excluded from the traversal order used by the IR builder. The IR builder receives them as back-edge metadata to annotate `continue_as_new` points (V2).

---

## 7. Edge Resolution Examples

### Example 1: IF node edge resolution

Graph edges:
```json
[
  { "id": "e1", "source": "n-if", "target": "n-notify", "edge_type": "TRUE" },
  { "id": "e2", "source": "n-if", "target": "n-flag", "edge_type": "FALSE" }
]
```

After normalizer handle resolution:
```json
[
  { "id": "e1", "source": "n-if", "target": "n-notify", "source_handle": "true", "target_handle": "input", "edge_type": "TRUE" },
  { "id": "e2", "source": "n-if", "target": "n-flag", "source_handle": "false", "target_handle": "input", "edge_type": "FALSE" }
]
```

### Example 2: PARALLEL node branch edge resolution

Graph edges (3 branches):
```json
[
  { "id": "e1", "source": "n-parallel", "target": "n-fetch-users", "edge_type": "SUCCESS" },
  { "id": "e2", "source": "n-parallel", "target": "n-fetch-orders", "edge_type": "SUCCESS" },
  { "id": "e3", "source": "n-parallel", "target": "n-handle-error", "edge_type": "ERROR" }
]
```

After normalizer: `source_handle` is `"success"` for e1 and e2, `"error"` for e3. But all three point to the same output handle ID on the PARALLEL node. This is valid because PARALLEL has multiple outbound edges from the same `success` handle.

**Design issue:** Three edges all have `source_handle: "success"` but go to different targets. The handle ID alone doesn't distinguish which branch is which. The IR builder uses edge ordering (array index) to label branches: branch_0, branch_1, branch_N.

---

## 8. Edge Registry Risks

| Risk | Severity | Notes |
|---|---|---|
| PARALLEL branch order is non-deterministic if the graph JSON serializer doesn't preserve array order | Medium | Always use array-preserving serialization; document that branch order = edge array order |
| IF node with two TRUE edges (user error) — validator must catch this with `MULTIPLE_BRANCH` | Medium | Validator must count edges by type per source node |
| LOOP edge treated as a regular edge by a naive topological sort → infinite loop in algorithm | High | Cycle detector must explicitly skip LOOP edges before sort |
| Handle inference from `edge_type` may conflict with explicit `source_handle` set by the UI | Low | Normalizer rule: explicit `source_handle` takes precedence over inferred; log warning if they conflict |
| PARALLEL SUCCESS edges are ambiguous — "this is a branch edge" vs "this is sequential success" | Medium | Rule: SUCCESS edge from a PARALLEL source is always a branch. This must be documented and enforced by the validator (cannot have a single SUCCESS edge from PARALLEL — minimum 2 required) |

---

## 9. Alternatives Considered

### Alternative A: Untyped edges (label-only routing)

**Rejected.** Routing based solely on `source_handle` names (e.g., handle named `"true"`) would work but requires the compiler to know the semantic meaning of handle names per node type. This couples the compiler to handle naming conventions rather than explicit types. `edge_type` is more robust.

### Alternative B: Per-node-type edge schemas

**Deferred to V2.** Instead of a shared EdgeType enum, each node type could define its own allowed connection types (with full JSON Schema validation). This would allow richer per-type rules but significantly complicates the edge registry and validator. V1 uses the shared enum with the connection validity matrix.

### Alternative C: Edges carry Zigflow DSL routing keys directly

**Rejected.** Edge types being Zigflow-specific (e.g., edge_type: ZIGFLOW_SWITCH_CASE) would couple the graph schema to a specific DSL backend. The graph schema is DSL-agnostic by design to allow future backends.
