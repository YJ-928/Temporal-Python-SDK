# 03 — Node Mapping: Graph Node → Zigflow DSL

## Overview

This document defines the exact Zigflow DSL output for each node type. The compiler is responsible for this mapping. Nothing else produces or modifies task blocks.

---

## START

**Role:** Graph-only. Marks the traversal root.
**DSL output:** None. START is consumed by the compiler as the traversal entry point and emits zero task blocks.

---

## END

**Role:** Graph-only. Marks the traversal terminal.
**DSL output:** None. END is consumed by the compiler as the termination sentinel and emits zero task blocks.

---

## VARIABLE → `set` / `export`

### Subtype: `operation: "set"`

**Node `data`:**
```json
{
  "name": "captureInput",
  "operation": "set",
  "assignments": {
    "userId": "${ $input.userId }",
    "requestId": "${ uuid }"
  }
}
```

**Zigflow DSL output:**
```yaml
- captureInput:
    set:
      userId: ${ $input.userId }
      requestId: ${ uuid }
```

---

### Subtype: `operation: "export"`

**Node `data`:**
```json
{
  "name": "persistUser",
  "operation": "export",
  "assignments": {
    "fetchedUser": "${ . }"
  }
}
```

**Zigflow DSL output:**
```yaml
- persistUser:
    export:
      as: "${ $context + {fetchedUser: .} }"
```

Note: The compiler always uses the merge form `$context + {...}` for `export` to avoid overwriting existing context keys.

---

## ACTION

### Subtype: `call:http`

**Node `data`:**
```json
{
  "name": "fetchUser",
  "subtype": "call:http",
  "method": "get",
  "endpoint": "https://api.example.com/users/1",
  "outputAs": "user"
}
```

**Zigflow DSL output:**
```yaml
- fetchUser:
    call: http
    with:
      method: get
      endpoint: https://api.example.com/users/1
    output:
      as:
        user: ${ . }
```

If `outputAs` is absent, the `output` block is omitted.

---

### Subtype: `call:grpc`

**Node `data`:**
```json
{
  "name": "callUserService",
  "subtype": "call:grpc",
  "endpoint": "grpc://user-service:50051/UserService/GetUser"
}
```

**Zigflow DSL output:**
```yaml
- callUserService:
    call: grpc
    with:
      endpoint: grpc://user-service:50051/UserService/GetUser
```

---

### Subtype: `run:script`

**Node `data`:**
```json
{
  "name": "transformData",
  "subtype": "run:script",
  "language": "python",
  "code": "result = input['value'] * 2\nreturn result"
}
```

**Zigflow DSL output:**
```yaml
- transformData:
    run:
      script:
        language: python
        code: |
          result = input['value'] * 2
          return result
```

---

### Subtype: `run:shell`

**Node `data`:**
```json
{
  "name": "runMigration",
  "subtype": "run:shell",
  "command": "python manage.py migrate"
}
```

**Zigflow DSL output:**
```yaml
- runMigration:
    run:
      shell:
        command: python manage.py migrate
```

---

## WORKFLOW → `run: { workflow: ... }`

**Node `data`:**
```json
{
  "name": "runOrderFlow",
  "workflowType": "order-processing",
  "taskQueue": "order-queue",
  "input": "${ $data.userId }"
}
```

**Zigflow DSL output:**
```yaml
- runOrderFlow:
    run:
      workflow:
        name: order-processing
        taskQueue: order-queue
        input: ${ $data.userId }
```

If `taskQueue` is absent, the `taskQueue` key is omitted (Zigflow inherits from parent).

---

## IF → `switch`

**Node `data`:**
```json
{
  "name": "routeByStatus",
  "cases": [
    { "label": "active",   "when": "${ $data.user.status == \"active\" }" },
    { "label": "inactive", "when": "${ $data.user.status == \"inactive\" }" }
  ],
  "default": true
}
```

**Edges from this node (in order):**
```
edge: if-1 → active-handler-node
edge: if-1 → inactive-handler-node
edge: if-1 → default-handler-node  (only if "default": true)
```

**Zigflow DSL output:**
```yaml
- routeByStatus:
    switch:
      - active:
          when: ${ $data.user.status == "active" }
          then: <task-name-of-child-0>
      - inactive:
          when: ${ $data.user.status == "inactive" }
          then: <task-name-of-child-1>
      - default:
          then: <task-name-of-child-2>
```

### How the compiler resolves `then` targets

- The compiler BFS-walks the tree.
- For an IF node, outgoing edges are ordered as supplied in the `edges` array.
- `cases[i].then` is resolved to the task name of the `i`-th child node.
- If `"default": true`, an additional `default` case is appended pointing to the last child edge's target.
- The `then` value is the DSL task name of the target node (i.e., the `data.name` or `id` of that node).

### Edge rule

Edges from IF carry **no condition expressions**. All `when` expressions live in `data.cases[i].when`.

---

## PARALLEL → `fork`

### `compete: false` — all branches must complete

**Node `data`:**
```json
{
  "name": "runInParallel",
  "compete": false
}
```

**Edges from this node:**
```
edge: parallel-1 → branch-a-node
edge: parallel-1 → branch-b-node
```

**Zigflow DSL output:**
```yaml
- runInParallel:
    fork:
      compete: false
      branches:
        - branch0:
            do:
              <subtree of branch-a-node emitted here>
        - branch1:
            do:
              <subtree of branch-b-node emitted here>
```

### `compete: true` — race, first wins

**Node `data`:**
```json
{
  "name": "raceToComplete",
  "compete": true
}
```

**Zigflow DSL output:**
```yaml
- raceToComplete:
    fork:
      compete: true
      branches:
        - branch0:
            do:
              <subtree of branch-a-node>
        - branch1:
            do:
              <subtree of branch-b-node>
```

### Branch naming convention

Branch names are positional: `branch0`, `branch1`, `branch2`, … in the order edges appear in the `edges` array.

### Important constraint

Each branch of a PARALLEL node must be a **self-contained subtree** that eventually reaches the same join node (or END). The compiler emits each branch as a nested `do` block. No shared state is written across branches (that would require `export` nodes inside each branch).

---

## WAIT

### Subtype: `duration`

**Node `data`:**
```json
{
  "name": "pauseFor5s",
  "subtype": "duration",
  "seconds": 5
}
```

**Zigflow DSL output:**
```yaml
- pauseFor5s:
    wait:
      seconds: 5
```

Other duration units: `minutes`, `hours`. Only one unit per node.

---

### Subtype: `signal`

**Node `data`:**
```json
{
  "name": "waitForApproval",
  "subtype": "signal",
  "signalId": "approve",
  "signalType": "signal"
}
```

**Zigflow DSL output:**
```yaml
- waitForApproval:
    listen:
      to:
        one:
          with:
            id: approve
            type: signal
```

`signalType` defaults to `"signal"` if absent. For event-driven patterns, it may be set to `"event"`.

---

## Task Name Resolution

Task names in the Zigflow `do` list come from the node in this priority order:

1. `data.name` — if set and non-empty, use this.
2. `node.id` — fallback to the node's ID.

All task names must be **unique within the workflow**. The compiler must detect and reject duplicates during validation.

---

## Summary Table

| Node Type | DSL Task | DSL Key |
|---|---|---|
| START | (none) | — |
| END | (none) | — |
| VARIABLE (`set`) | `set` | `{ key: expr, ... }` |
| VARIABLE (`export`) | `export` | `{ as: "${ $context + {...} }" }` |
| ACTION (`call:http`) | `call: http` | `with: { method, endpoint }` |
| ACTION (`call:grpc`) | `call: grpc` | `with: { endpoint }` |
| ACTION (`run:script`) | `run: { script }` | `{ language, code }` |
| ACTION (`run:shell`) | `run: { shell }` | `{ command }` |
| WORKFLOW | `run: { workflow }` | `{ name, taskQueue?, input? }` |
| IF | `switch` | `[{ label: { when, then } }, ...]` |
| PARALLEL | `fork` | `{ compete, branches: [...] }` |
| WAIT (`duration`) | `wait` | `{ seconds | minutes | hours }` |
| WAIT (`signal`) | `listen` | `{ to: { one: { with: { id, type } } } }` |
