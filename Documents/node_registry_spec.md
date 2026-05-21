# Node Registry Specification

> **Status:** R&D / Design Phase
> **Purpose:** Defines the YAML schema for node definitions, the catalog of all 8 V1 node types, their config contracts, and how the registry drives the compiler.

---

## 1. What Is the Node Registry?

The Node Registry is a data-driven catalog of node type definitions. Each node type is described by a YAML file in `registry/node_definitions/`. The compiler reads these definitions at startup and uses them for:

- **Validation:** which config fields are required?
- **Normalization:** which default values should be filled in?
- **Handle resolution:** what are the valid output handles on this node type?
- **Generator dispatch:** which Zigflow task type does this node map to?
- **UI:** what config form fields should the canvas render?

**Core design principle:** Adding a new node type in V2 requires only a new YAML file. No compiler code changes. The YAML file is the single source of truth for a node type's behavior contract.

This principle holds fully for simple node types (ACTION, VARIABLE, WAIT, WORKFLOW). It holds partially for structural node types (IF, PARALLEL) because branch grouping in the IR builder has structural logic that cannot be fully expressed in YAML.

---

## 2. Node Definition YAML Schema

```yaml
# Canonical schema for a node_definitions/*.yaml file

type: STRING              # NodeType enum value (uppercase)
description: STRING       # Human-readable description

inputs:
  - id: STRING            # handle id — must be unique within node
    label: STRING         # UI label (optional)

outputs:
  - id: STRING
    label: STRING

config_schema:            # JSON Schema (Draft 7) for the node's config object
  type: object
  required: [field1, ...]
  properties:
    field1:
      type: STRING        # json schema types: string, number, integer, boolean, object, array
      description: STRING
      enum: [...]         # allowed values (optional)
  additionalProperties: false | true

zigflow_task:             # maps config values → Zigflow task type
  null                    # for graph anchors (START, END)
  STRING                  # single task type (e.g. "set", "switch", "fork")
  dict:                   # dispatch by config key
    config_value: "task_type"

templates:                # maps config values → template file name (optional)
  config_value: template_name

validation:               # extra structural rules (optional)
  outbound_edges:
    required: [edge_type, ...]
    count: integer
  outbound_branch_edges:
    min_count: integer
```

---

## 3. V1 Node Catalog (8 Types)

### 3.1 START

```
Role         Graph anchor — entry point of the workflow
Zigflow task None — emits no DSL task
Handles      Output: [output]
Config       inputSchema (optional JSON Schema for input validation)
```

**Config example:**
```json
{
  "inputSchema": {
    "type": "object",
    "properties": {
      "userId": { "type": "string" },
      "amount": { "type": "number" }
    },
    "required": ["userId"]
  }
}
```

**Compiler behavior:** The normalizer uses `inputSchema` to document the workflow input contract in `document.metadata`. No task is emitted. The first edge from START determines the first item in the `do` list.

---

### 3.2 END

```
Role         Graph anchor — termination point
Zigflow task None — emits no DSL task
Handles      Input: [input]
Config       outputMapping (optional — maps output keys to jq expressions)
```

**Config example:**
```json
{
  "outputMapping": {
    "result": "${ $context.processResult }",
    "status": "${ $context.status }"
  }
}
```

**Compiler behavior:** If `outputMapping` is present, the normalizer inserts a synthetic VARIABLE node before END that emits the mapped output. This preserves the rule that END emits no task.

**Open question:** Is a synthetic VARIABLE node the right approach, or should the generator handle this inline? Adding a synthetic node changes the graph post-normalization, which affects the `normalized_graph_json` debug artifact and may surprise debuggers.

---

### 3.3 ACTION

```
Role         Execute an HTTP call, gRPC call, shell command, or embedded script
Zigflow task call: http | call: grpc | run: script | run: shell
Handles      Input: [input]   Output: [success, error]
Config       protocol (required), + protocol-specific fields
```

**Protocol dispatch table:**

| `protocol` | Zigflow task | Required config fields | Optional config fields |
|---|---|---|---|
| `http` | `call: http` | `method`, `endpoint` | `headers`, `body`, `outputKey`, `retry` |
| `grpc` | `call: grpc` | `method`, `endpoint` | `body`, `outputKey`, `retry` |
| `script` | `run: script` | `script` | `outputKey`, `retry` |
| `shell` | `run: shell` | `command` | `outputKey`, `retry` |

**Config example (http):**
```json
{
  "protocol": "http",
  "method": "POST",
  "endpoint": "https://api.example.com/orders",
  "headers": { "Content-Type": "application/json" },
  "body": { "userId": "${ $input.userId }", "item": "${ $input.item }" },
  "outputKey": "orderResult",
  "retry": "standardRetry"
}
```

**Expected Zigflow output (http with outputKey and retry):**
```yaml
- createOrder:
    call: http
    with:
      method: POST
      endpoint: https://api.example.com/orders
      headers:
        Content-Type: application/json
      body:
        userId: ${ $input.userId }
        item: ${ $input.item }
    retry: ${ $workflow.retries.standardRetry }
    output:
      as: "${ $context + {orderResult: .} }"
    export:
      as: "${ $context + {orderResult: .} }"
```

**Config example (shell):**
```json
{
  "protocol": "shell",
  "command": "echo ${ $input.name }",
  "outputKey": "shellOut"
}
```

**Design risk — ERROR edge handling:** The ACTION node has an `error` output handle. In a Zigflow DSL, error handling is done via `try`/`catch`. The compiler must decide: does an ERROR edge on an ACTION node wrap the task in a `try`/`catch` block, or is it a separate routing mechanism? This is an **open design question** with major impact on the IR builder.

**Option A:** Error edges cause the generator to wrap the task in `try: [...] catch: {do: [...]}`. The catch `do` block contains the error-path subtree.
**Option B:** Error edges are advisory only — the compiler ignores them and relies on Zigflow's default error propagation (activity retry + workflow failure).
**V1 recommendation:** Option B (simpler, avoids try/catch complexity in V1). Document the limitation.

---

### 3.4 VARIABLE

```
Role         Set workflow variables using jq expressions; optionally export to $context
Zigflow task set: {...}
Handles      Input: [input]   Output: [success]
Config       assignments (required), export (optional boolean)
```

**Config example:**
```json
{
  "assignments": {
    "requestId": "${ uuid }",
    "startedAt": "${ timestamp }",
    "status": "\"processing\""
  },
  "export": true
}
```

**Expected Zigflow output (with export: true):**
```yaml
- initVariables:
    set:
      requestId: ${ uuid }
      startedAt: ${ timestamp }
      status: "processing"
    export:
      as: "${ $context + {requestId: .requestId, startedAt: .startedAt, status: .status} }"
```

**When export is false (or omitted):** only `set` is emitted; variables are scoped to the current task's output, not persisted across tasks in `$context`.

**Design note:** The distinction between `set` (task-scoped) and `export` (context-persistent) maps directly to Zigflow's `set` vs `export` semantics. The VARIABLE node makes this explicit in its config.

---

### 3.5 IF

```
Role         Conditional routing based on a jq boolean expression
Zigflow task switch: [...]
Handles      Input: [input]   Output: [true, false]
Config       condition (required)
Validation   Must have exactly 1 TRUE edge and 1 FALSE edge (enforced by validator)
```

**Config example:**
```json
{
  "condition": "${ $context.user.active == true }"
}
```

**Expected Zigflow output:**
```yaml
- checkActive:
    switch:
      - when: "${ $context.user.active == true }"
        then:
          do:
            - notifyUser:
                call: http
                ...
      - then:
          do:
            - flagInactive:
                set:
                  status: "inactive"
```

**Critical design question — switch task structure in Zigflow DSL:**
The exact structure of `switch` in Zigflow's CNCF Serverless Workflow DSL v1.0.0 is not fully verified. Two possible structures:

**Structure A (inline do-blocks per case):**
```yaml
- decision:
    switch:
      - when: "${ condition }"
        then:
          do: [...]     ← true branch tasks inline
      - then:
          do: [...]     ← false branch tasks (default case)
```

**Structure B (named task references):**
```yaml
- decision:
    switch:
      - when: "${ condition }"
        then: taskNameA    ← jumps to a named task in the do list
      - then: taskNameB
```

Structure B implies the true/false branch tasks are not nested inside the switch but placed elsewhere in the `do` list with explicit naming. This would significantly affect the IR builder and generator design.

**Action required before implementation:** Inspect the Zigflow worker source code or test with a `switch` workflow to determine the actual accepted structure.

---

### 3.6 PARALLEL

```
Role         Execute 2+ branches concurrently; all-complete or first-wins
Zigflow task fork: {compete: bool, branches: [...]}
Handles      Input: [input]   Output: [success, error]
Config       compete (required), outputKey (optional)
Validation   Must have ≥ 2 non-ERROR outbound edges (enforced by validator)
```

**Config example (race — first wins):**
```json
{
  "compete": true,
  "outputKey": "winnerResult"
}
```

**Config example (all complete):**
```json
{
  "compete": false,
  "outputKey": "allResults"
}
```

**Expected Zigflow output (compete: true, 2 branches):**
```yaml
- raceToFetch:
    fork:
      compete: true
      branches:
        - fastPath:
            do:
              - getFromCache:
                  call: http
                  ...
        - slowPath:
            do:
              - getFromDB:
                  call: http
                  ...
```

**Design question — how are branches identified from the graph?**
The compiler needs to identify which downstream node belongs to which branch. Proposal: each non-ERROR outbound edge from the PARALLEL node starts a branch. The branch ends when its path reaches either the END node or a node that is also reachable from a different branch (convergence point).

Detecting the convergence point requires a graph algorithm: find the **lowest common dominator** of all branch paths. This is non-trivial. Alternative: require the UI to draw an explicit convergence node after the PARALLEL fork, which the compiler can identify as the join point.

**V1 recommendation:** Require UI to connect branch paths to the PARALLEL node's `success` handle, which acts as the join signal. The compiler collects all non-ERROR edges from PARALLEL as branch start points, and renders each branch as a mini-subtree walking the graph until a node that also has an incoming edge from another branch is reached.

---

### 3.7 WAIT

```
Role         Durable pause — timer sleep or external signal listener
Zigflow task wait: {duration} (timer) | listen: {to: ...} (signal)
Handles      Input: [input]   Output: [success, error]
Config       mode (required), + mode-specific fields
Templates    wait_timer (timer mode) | wait_signal (signal mode)
```

**mode: timer config:**
```json
{
  "mode": "timer",
  "duration": { "minutes": 30 }
}
```

**mode: signal config:**
```json
{
  "mode": "signal",
  "signalName": "approve",
  "signalType": "signal",
  "timeout": { "minutes": 60 },
  "outputKey": "approvalPayload"
}
```

**Why two separate templates?** Timer and signal produce entirely different Zigflow task structures (`wait` vs `listen`). A single template cannot express both with a simple placeholder substitution. The mode value selects the template file: `mode: timer → wait_timer.yaml`, `mode: signal → wait_signal.yaml`.

**Expected output (timer):**
```yaml
- pause30min:
    wait:
      minutes: 30
```

**Expected output (signal):**
```yaml
- waitForApproval:
    metadata:
      timeout: 60m
    listen:
      to:
        one:
          with:
            id: approve
            type: signal
    export:
      as: "${ $context + {approvalPayload: .} }"
```

---

### 3.8 WORKFLOW

```
Role         Execute a child or external workflow as a sub-process
Zigflow task run: {workflow: ...} (child) | call: http (external)
Handles      Input: [input]   Output: [success, error]
Config       type (required), workflowType (required), taskQueue (required), input, outputKey
Templates    workflow_child (child type) | workflow_external (external type)
```

**type: child config:**
```json
{
  "type": "child",
  "workflowType": "process-order",
  "taskQueue": "order-queue",
  "input": { "orderId": "${ $context.orderId }" },
  "outputKey": "orderResult"
}
```

**Expected output (child):**
```yaml
- runProcessOrder:
    run:
      workflow:
        name: process-order
        taskQueue: order-queue
        input: ${ {orderId: $context.orderId} }
    export:
      as: "${ $context + {orderResult: .} }"
```

**type: external config:**
```json
{
  "type": "external",
  "workflowType": "notification-service",
  "taskQueue": "notif-queue",
  "input": { "userId": "${ $context.userId }" },
  "outputKey": "notifResult"
}
```

**Open question:** Zigflow's `run: workflow` DSL — what is the exact structure for specifying the taskQueue and namespace for a child workflow? The Zigflow worker source code must be consulted before finalizing this template.

---

## 4. V2 Node Types (Planned, Not V1)

| Node Type | Description | Zigflow mapping |
|---|---|---|
| `LOOP` | Explicit loop node with iteration counter and break condition | `for: {each, in, do}` or `continue_as_new` bridge |
| `HUMAN_APPROVAL` | Waits for human decision via external signal + timeout + escalation | Composite: `listen` + `wait` + optional retry |
| `AI_AGENT` | Calls an LLM or AI service with structured input/output | `call: http` with streaming support |
| `MCP_TOOL` | Invokes an MCP tool endpoint | `call: http` with MCP protocol headers |

Adding these in V2 requires only new YAML definition files and template files — no compiler code changes, as long as their behavior maps to existing IR task types.

---

## 5. Config Validation Strategy

There are two points where config can be validated:

**Option A: At the raw graph level (pre-normalization)**
- Validator loads node registry and checks required fields
- Errors are surfaced immediately with precise node IDs
- Requires validator to depend on the registry (coupling)

**Option B: At normalization time**
- Normalizer checks config after defaults are filled
- Cleaner separation: validator is pure structural, normalizer is semantic
- Error reporting is one stage later

**Recommendation:** Option B for V1. The validator handles structural rules only (START/END existence, cycle detection, handle existence). The normalizer handles semantic validation (required config fields, valid enum values). This separation keeps the validator fast and dependency-free.

---

## 6. Registry Risks

| Risk | Severity | Notes |
|---|---|---|
| IF/PARALLEL structural behavior cannot be fully expressed in YAML — requires compiler special cases | Medium | Document the exception; plan to externalize in V3 |
| Node type added in YAML but generator has no renderer for its `task_type` → runtime error | Medium | Generator should raise a clear error: `UnknownTaskType: {type}` |
| config_schema drift — YAML schema and normalizer validation logic diverge | Low | Single source of truth (YAML) reduces drift; normalizer reads schema at runtime |
| YAML parse errors in node definition files → registry silent failure | Low | Registry should validate on load and raise on malformed files |
