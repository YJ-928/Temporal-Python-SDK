# DSL Builders — Agent Reference

## Rules (apply to every builder)

- One file per node type in `poc-dsl-compiler/builders/`.
- One public function per file: `build_<type>(node: dict) -> dict | None`.
- Pure functions — no side effects, no imports, no global state.
- Task name is always derived from `node["id"]` + a fixed suffix (see each builder).
- The returned dict is a **single-key dict** where the key is the task name and the value is the task body. This is what `dsl_generator.py` appends to `dsl["do"]`.
- All Zigflow expressions use `${ }` syntax. In Python f-strings, braces are escaped as `{{` and `}}`:
  ```python
  f"${{ $input.{field} }}"   # produces:  ${ $input.location }
  f"${{ .{ctx_var} }}"       # produces:  ${ .user_location }
  ```

---

## Builder Reference

### `terminal_builder.py` — START and END

```python
def build_terminal(node: dict) -> None
```

- Returns `None`. Both START and END emit no DSL tasks.
- `dsl_generator.py` silently skips `None` returns.
- Both node types share this single function (registered twice in `NODE_BUILDERS`).

---

### `input_builder.py` — INPUT node

**Node data contract:**
```json
{
  "type": "INPUT",
  "data": {
    "inputs": [
      { "field": "location",      "store_as": "user_location", "type": "string" },
      { "field": "date_of_birth", "store_as": "dob",           "type": "string" }
    ]
  }
}
```

**Task name:** `{node_id}_capture`

**DSL output:**
```json
{
  "N2_capture": {
    "set": {
      "user_location": "${ $input.location }",
      "dob":           "${ $input.date_of_birth }"
    }
  }
}
```

**Logic:** Reads `node["data"]["inputs"]`. For each entry: key = `store_as`, value = `${ $input.<field> }`. Multiple fields in one `set` task.

**DSL semantics:** `set` with `${ $input.* }` emits a Zigflow set task that reads named fields from the workflow input. The runtime resolves the expression at execution time — the builder only constructs the DSL fragment.

---

### `action_builder.py` — ACTION node

**Node data contract:**
```json
{
  "type": "ACTION",
  "data": {
    "operation": "send_notification",
    "inputs": {
      "value": "user_location"
    },
    "output": "notification_status"
  }
}
```

- `operation`: string used as URL path segment and task name suffix.
- `inputs`: `{param_name: context_var}` — param is the request body key, context_var is the workflow variable to read.
- `output`: workflow variable name where the response is stored.

**Task name:** `{node_id}_{operation}`

**DSL output:**
```json
{
  "N3_send_notification": {
    "call": "http",
    "with": {
      "method": "post",
      "endpoint": "http://localhost:8080/send_notification",
      "body": {
        "value": "${ .user_location }"
      }
    },
    "output": {
      "as": {
        "notification_status": "${ . }"
      }
    }
  }
}
```

**Logic:**
- `body`: `{param: f"${{ .{ctx_var} }}"}` — reads each context variable from current workflow data.
- `endpoint`: `http://localhost:8080/{operation}` — hardcoded host for V1.
- `output.as`: `{output_var: "${ . }"}` — captures the full HTTP response body as the named variable.
- `method` is always `"post"` in V1.

**DSL semantics:** `call: http` emits a Zigflow HTTP task. The runtime decides execution (scheduling, retries, timeouts — all Zigflow + Temporal concerns, not the builder's). `${ . }` in `output.as` expresses "capture the full response". `${ .<var> }` expresses "read this variable from the current data context".

---

### `output_builder.py` — OUTPUT node

**Node data contract:**
```json
{
  "type": "OUTPUT",
  "data": {
    "outputs": [
      { "field": "notification_status", "type": "string" },
      { "field": "location_data",       "type": "string" }
    ]
  }
}
```

**Task name:** `{node_id}_expose`

**DSL output:**
```json
{
  "N5_expose": {
    "set": {
      "notification_status": "${ .notification_status }",
      "location_data":       "${ .location_data }"
    }
  }
}
```

**Logic:** Reads `node["data"]["outputs"]`. For each entry: key = `field`, value = `${ .<field> }`. Multiple fields in one `set` task.

**DSL semantics:** `set` with `${ .<field> }` emits a Zigflow set task that reads named fields from the current data context. The runtime resolves context population — the builder only constructs the DSL fragment.

---

### `wait_builder.py` — WAIT node

**Node data contract:**
```json
{
  "type": "WAIT",
  "data": {
    "duration": {
      "seconds": 30
    }
  }
}
```

Supported duration keys: `seconds`, `minutes`, `hours`. Exactly one key per node.

**Task name:** `{node_id}_wait`

**DSL output:**
```json
{
  "N4_wait": {
    "wait": {
      "seconds": 30
    }
  }
}
```

**Logic:** `node["data"]["duration"]` is passed directly into the `wait` task body — no transformation needed. The data contract already matches the Zigflow schema.

**DSL semantics:** `wait` emits a Zigflow wait task. The runtime decides execution (durable timer behavior, crash recovery — all Zigflow + Temporal concerns, not the builder's).

---

### `dsl_boilerplate_builder.py` — DSL document header

Not a node builder. Called once by `dsl_generator.generate_dsl()` to initialise the DSL dict.

```python
def generate_dsl_boilerplate(dsl_version, version, workflow_type, task_queue) -> dict
```

**Returns:**
```json
{
  "document": {
    "dsl": "1.0.0",
    "taskQueue": "zigflow",
    "workflowType": "compiled-workflow",
    "version": "1.0.0",
    "metadata": {}
  },
  "do": []
}
```

`metadata: {}` is required by the Zigflow schema even when empty.

---

## Templates (reference only)

Files in `poc-dsl-compiler/templates/` are **not used at runtime**. They document what each active builder produces.

| Template file | Corresponding builder | Status |
|---|---|---|
| `action_input.json` | `input_builder` | ✅ matches builder output |
| `action_output.json` | `output_builder` | ✅ matches builder output |
| `action_http.json` | `action_builder` | ✅ matches builder output |
| `dsl_boilerplate.json` | `dsl_boilerplate_builder` | ✅ matches builder output |
| `wait_timer.json` | `wait_builder` | ✅ matches builder output |
| `action_script.json` | no builder yet | ❌ deferred |
| `action_shell.json` | no builder yet | ❌ deferred |
| `if_switch.json` | no builder yet | ❌ deferred |
| `parallel.json` | no builder yet | ❌ deferred |
| `variable.json` | no builder yet | ❌ deferred |
| `wait_signal.json` | no builder yet | ❌ deferred |
| `workflow.json` | no builder yet | ❌ deferred |

**Rule:** When adding a new builder, update the corresponding template to match the builder's exact output and mark it ✅ in this table.

---

## Template Rules

Files in `poc-dsl-compiler/templates/` exist for documentation purposes only.

- Templates are **never imported** by any Python module
- Templates are **never loaded** at runtime
- Templates are **never executed**
- Templates serve as **reference fragments** showing what each builder produces
- Template and builder must stay synchronized — if they disagree, the builder is the source of truth; update the template to match

| Status | Meaning |
|---|---|
| ✅ implemented | Active builder exists and template matches its output exactly |
| ⏳ deferred | No builder yet; template documents the intended future DSL shape |
| — unused | No builder and no current plan |

If a template disagrees with a builder's actual output, **the builder is the source of truth**. Update the template to match.

---

## Adding a New Builder — Checklist

1. Create `builders/<type_lower>_builder.py` with `build_<type>(node: dict) -> dict`.
2. Add import + dispatch entry to `dsl_generator.py` `NODE_BUILDERS`.
3. Update the corresponding template in `templates/` to match builder output exactly.
4. Add an input JSON in `input/workflow_outputs/` that exercises the new node.
5. Run `python3 main.py <workflow>` → confirm output generates.
6. Run `zigflow validate output/<workflow>_dsl_schema.json` → must pass ✅.
7. Update the Node Types table in `.github/features/dsl_compiler.md`.
8. Update the Templates table in this file.
