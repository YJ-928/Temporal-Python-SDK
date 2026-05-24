# Workflow JSON Contract (Frozen — V1)

> **Status:** Frozen. Do not change without updating `compiler_context.md` and `.github/copilot-instructions.md`.
> **Last updated:** May 2026

---

## 1. Top-Level Structure

The compiler accepts a single JSON object with exactly two required keys:

```json
{
  "nodes": [],
  "edges": []
}
```

No other top-level keys are required or processed in V1. Additional keys (e.g. `version`, `metadata`) may be present but are ignored by the current compiler.

---

## 2. Node Schema

Every node is a JSON object with the following shape:

```json
{
  "id": "<string>",
  "type": "<node-type>",
  "data": {}
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | yes | string | Unique within the graph. Used as edge `source` / `target`. |
| `type` | yes | string enum | Must be one of the five V1 node types (see below). |
| `data` | conditional | object | Required for `INPUT`, `ACTION`, `OUTPUT`. Omitted for `START` and `END`. |

`position` fields (from UI tools) are ignored. The compiler never uses coordinate data.

---

## 3. Frozen V1 Node Types

These are the **only** node types the compiler handles. Any other type in the input will be unhandled.

### START

```json
{ "id": "N1", "type": "START" }
```

- No `data` field.
- Exactly one `START` node must exist in every valid graph.
- Emits **no** DSL task block.

---

### END

```json
{ "id": "N5", "type": "END" }
```

- No `data` field.
- Exactly one `END` node must exist in every valid graph.
- Emits **no** DSL task block.

---

### INPUT

Captures external input fields and stores them as named runtime variables.

```json
{
  "id": "N2",
  "type": "INPUT",
  "data": {
    "inputs": [
      {
        "field": "name",
        "store_as": "user_name",
        "type": "string"
      },
      {
        "field": "date_of_birth",
        "store_as": "dob",
        "type": "date"
      }
    ]
  }
}
```

| `data` field | Required | Type | Notes |
|---|---|---|---|
| `inputs` | yes | array | One or more input field definitions |
| `inputs[].field` | yes | string | The key in the external workflow input payload |
| `inputs[].store_as` | yes | string | The runtime variable name used by downstream nodes |
| `inputs[].type` | yes | string | Informational only — `string`, `date`, `integer`, `boolean` |

**DSL output (planned):**
```yaml
- captureInput:
    set:
      user_name: ${ $input.name }
      dob: ${ $input.date_of_birth }
```

---

### ACTION

Transforms runtime variables by invoking a named operation.

```json
{
  "id": "N3",
  "type": "ACTION",
  "data": {
    "operation": "greet",
    "inputs": {
      "name": "user_name"
    },
    "output": "message"
  }
}
```

| `data` field | Required | Type | Notes |
|---|---|---|---|
| `operation` | yes | string | The name of the operation to invoke (becomes the activity name in DSL) |
| `inputs` | yes | object | Map of `{argument_name → runtime_variable_name}` |
| `output` | yes | string | The runtime variable name where the result is stored |

**DSL output (planned):**
```yaml
- greet:
    call: activity
    with:
      name: greet
      arguments:
        name: ${ $data.user_name }
    output:
      as: ${ {message: .} }
```

---

### OUTPUT

Exposes named runtime variables as the workflow result.

```json
{
  "id": "N4",
  "type": "OUTPUT",
  "data": {
    "outputs": [
      {
        "field": "message",
        "type": "string"
      }
    ]
  }
}
```

| `data` field | Required | Type | Notes |
|---|---|---|---|
| `outputs` | yes | array | One or more output field definitions |
| `outputs[].field` | yes | string | The runtime variable name to expose |
| `outputs[].type` | yes | string | Informational only — `string`, `integer`, `boolean` |

**DSL output (planned):**
```yaml
- exposeOutput:
    set:
      message: ${ $context.message }
```

---

## 4. Edge Schema

Every edge is a JSON object with exactly three fields:

```json
{
  "id": "E1",
  "source": "N1",
  "target": "N2"
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | yes | string | Unique within the graph |
| `source` | yes | string | ID of the source node (must exist in `nodes`) |
| `target` | yes | string | ID of the target node (must exist in `nodes`) |

**Critical rule: edges carry no business data.** There is no `data`, `condition`, `label`, or `sourceHandle` field. All execution logic belongs in node `data`. This is a deliberate correction from the V0 prototype (`poc-react-flow`) where edges carried conditional routing logic.

---

## 5. Complete Example — Linear Workflow

`poc-dsl-compiler/examples/workflow_1_output.json`

```json
{
  "nodes": [
    { "id": "N1", "type": "START" },
    {
      "id": "N2",
      "type": "INPUT",
      "data": {
        "inputs": [
          { "field": "name", "store_as": "user_name", "type": "string" }
        ]
      }
    },
    {
      "id": "N3",
      "type": "ACTION",
      "data": {
        "operation": "greet",
        "inputs": { "name": "user_name" },
        "output": "message"
      }
    },
    {
      "id": "N4",
      "type": "OUTPUT",
      "data": {
        "outputs": [{ "field": "message", "type": "string" }]
      }
    },
    { "id": "N5", "type": "END" }
  ],
  "edges": [
    { "id": "E1", "source": "N1", "target": "N2" },
    { "id": "E2", "source": "N2", "target": "N3" },
    { "id": "E3", "source": "N3", "target": "N4" },
    { "id": "E4", "source": "N4", "target": "N5" }
  ]
}
```

---

## 6. Complete Example — Branching Workflow

`poc-dsl-compiler/examples/workflow_2_output.json`

A single `INPUT` node fans out to two parallel `ACTION` → `OUTPUT` branches. Both `OUTPUT` nodes wire to the shared `END` node.

```
START → INPUT → ACTION_greet → OUTPUT_message → END
                ↘ ACTION_calc_age → OUTPUT_age ↗
```

---

## 7. Graph Invariants (V1)

These invariants must hold for the compiler to process a graph correctly. The V1 compiler does not validate them — they are assumed to be satisfied by the input.

| Invariant | Rule |
|---|---|
| Exactly one START | `count(type == "START") == 1` |
| Exactly one END | `count(type == "END") == 1` |
| No orphan nodes | Every node is reachable from `START` |
| No cycles | The graph is a DAG |
| Valid edge references | Every `source` and `target` ID exists in `nodes` |
| Unique node IDs | No two nodes share the same `id` |
| Unique edge IDs | No two edges share the same `id` |

---

## 8. Node Types NOT in V1

The following node types are explicitly deferred. Do not add them to the compiler without updating this contract.

| Node Type | Reason deferred |
|---|---|
| `IF` | Requires conditional branch logic and edge handle matching |
| `WAIT` | Requires timer / signal semantics not yet modelled |
| `VARIABLE` | Subsumed by `INPUT` for V1; complex export logic deferred |
| `WORKFLOW` | Sub-workflow invocation requires runtime integration |
| `PARALLEL` | Fork/join semantics require branch grouping in the DSL builder |
