# DSL Builders — Agent Reference

## Rules (apply to every builder)

- One file per node type in `poc-dsl-compiler/builders/`.
- One public function per file: `build_<type>(node: dict, *, traversal_entry=None, compiler_context=None) -> dict | None`.
  - `traversal_entry`: a `TraversalEntry` dict (see `utils/traversal_types.py`). Passed by `dsl_generator.generate_dsl()` for every call. **Always accept it; never omit it.**
  - `compiler_context`: **deprecated**. Always `None` or `{}`. Accept it for signature consistency but never read it.
- Pure functions — no side effects, no global state.
- **`then: end` injection:** if `traversal_entry and traversal_entry["is_terminal"]` is True, add `"then": "end"` to the top-level task body dict. This is done by the builder, not by `dsl_generator.py`.
- Task name is always derived from `node["id"]` + a fixed suffix (see each builder).
- The returned dict is a **single-key dict** where the key is the task name and the value is the task body. This is what `dsl_generator.py` appends to `dsl["do"]`.
- `terminal_builder` (START, END) returns `None`. `dsl_generator.py` silently skips `None` returns.
- All Zigflow expressions use `${ }` syntax. In Python f-strings, braces are escaped as `{{` and `}}`:
  ```python
  f"${{ $input.{field} }}"    # produces:  ${ $input.location }
  f"${{ $context.{var} }}"    # produces:  ${ $context.user_location }
  f"${{ .{field} }}"          # produces:  ${ .notification_status }
  ```

---

## Builder Reference

### `terminal_builder.py` — START and END

```python
def build_terminal(node: dict, *, traversal_entry=None, compiler_context=None) -> None
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
    },
    "export": {
      "as": "${ $context + {user_location: .user_location, dob: .dob} }"
    }
  }
}
```

**With `is_terminal` (INPUT is the last node before END):**
```json
{
  "N2_capture": {
    "set": { ... },
    "export": { "as": "..." },
    "then": "end"
  }
}
```

**Logic:** Reads `node["data"]["inputs"]`. For each entry: `set` key = `store_as`, value = `${ $input.<field> }`. The `export.as` expression merges all captured variables into `$context` using `${ $context + {var: .var, ...} }` syntax, so they persist across subsequent tasks and parallel branches.

**DSL semantics:** `set` with `${ $input.* }` reads named fields from the workflow input. `export.as` persists those values into `$context` so they remain accessible even after a later `call: http` task replaces the flowing data context via `output.as`.

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
        "value": "${ $context.user_location }"
      }
    },
    "output": {
      "as": {
        "notification_status": "${ . }"
      }
    },
    "export": {
      "as": "${ $context + {notification_status: .notification_status} }"
    }
  }
}
```

**With `is_terminal`:** adds `"then": "end"` inside the task body (same level as `call`, `with`, `output`, `export`).

**Logic:**
- `body`: `{param: f"${{ $context.{ctx_var} }}"}` — reads **from `$context`** (not from transient flowing data). This ensures inputs remain valid even if a previous ACTION's `output.as` has replaced the current data context.
- `endpoint`: `http://localhost:8080/{operation}` — hardcoded host in V1.
- `output.as`: `{output_var: "${ . }"}` — captures the full HTTP response body as the named variable.
- `export.as`: `${ $context + {output_var: .output_var} }` — persists the output variable into `$context` so chained ACTION nodes and parallel branches can access it.
- `method` is always `"post"` in V1.

**DSL semantics:** `call: http` emits a Zigflow HTTP activity task. `${ $context.<var> }` reads from persisted context; `${ . }` captures the full response.

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

**DSL output (normal — no preceding PARALLEL):**
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

**DSL output (convergence — follows a PARALLEL block):**
```json
{
  "N5_expose": {
    "set": {
      "email_status":   "${ $context.email_status }",
      "profile_status": "${ $context.profile_status }"
    },
    "then": "end"
  }
}
```

**With `is_terminal`:** adds `"then": "end"` inside the task body.

**Logic:** Reads `node["data"]["outputs"]`. For each entry: key = `field`. Value expression depends on `traversal_entry.get("reads_from_context")`:
- `reads_from_context = False` (normal): `${ .<field> }` — reads from transient flowing data.
- `reads_from_context = True` (post-PARALLEL convergence): `${ $context.<field> }` — reads from persisted context, because parallel branch ACTIONs write results to `$context`, not to transient data.

Multiple fields share one `set` task.

**DSL semantics:** `set` shapes the workflow output. The `reads_from_context` distinction is required because `fork` branches run in isolated data contexts; their results only survive in `$context`.

---

### `wait_builder.py` — WAIT node

**Node data contract:**

WAIT nodes use `mode` + `config` (not `duration` directly):

```json
{
  "type": "WAIT",
  "data": {
    "mode": "duration",
    "config": { "seconds": 30 }
  }
}
```

or for signal-based waits:
```json
{
  "type": "WAIT",
  "data": {
    "mode": "listen",
    "config": { "signal": "approval" }
  }
}
```

- `mode`: `"duration"` or `"listen"`.
- `config` for `duration`: one time-unit key — `seconds`, `minutes`, or `hours`, integer value.
- `config` for `listen`: `{"signal": "<signal-name>"}` — the Temporal signal name to wait for.

**Task name:** `{node_id}_wait`

**DSL output — duration mode:**
```json
{
  "N4_wait": {
    "wait": { "seconds": 30 }
  }
}
```

**DSL output — listen mode:**
```json
{
  "N4_wait": {
    "listen": {
      "to": {
        "one": {
          "with": { "id": "approval" }
        }
      }
    }
  }
}
```

**With `is_terminal`:** adds `"then": "end"` inside the task body in both modes.

**Logic:** Dispatches internally based on `node["data"]["mode"]`. Duration mode passes `config` dict directly to `wait`. Listen mode reads `config["signal"]` and wraps it in the Zigflow `listen.to.one.with.id` structure.

**Internal helpers:** `_build_wait_duration(node_id, config)` and `_build_wait_listen(node_id, config)` — private, not registered in `NODE_BUILDERS`.

**DSL semantics:** `wait` emits a durable Zigflow timer (Temporal-backed; survives Worker crash). `listen` emits a durable Zigflow signal handler (Temporal signal).

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

### `parallel_builder.py` — PARALLEL node

**Node data contract:**
```json
{
  "id": "N3",
  "type": "PARALLEL",
  "data": { "compete": false }
}
```

- `compete: false` — all branches must complete; results from all are available afterward.
- `compete: true` — race; first branch to complete wins; others are cancelled.
- `data.compete` defaults to `false` when absent.

**Task name:** `{node_id}_parallel`

**DSL output:**
```json
{
  "N3_parallel": {
    "fork": {
      "compete": false,
      "branches": [
        { "branch_0": { "do": [ { "N4_send_email": { "call": "http", ... } } ] } },
        { "branch_1": { "do": [ { "N5_create_profile": { "call": "http", ... } } ] } }
      ]
    }
  }
}
```

**Branches are named:** each branch is `{branch_id: {"do": [...]}}` — NOT anonymous `{"do": [...]}`. This is required by the Zigflow `fork` schema.

**Branch order:** sorted by `branch_id` key (`branch_0`, `branch_1`, …), which Phase A assigns in outgoing-edge declaration order.

**With `is_terminal`:** PARALLEL is **never terminal**. The convergence OUTPUT node after the fork handles `then: end`. Never inject `then: end` into a PARALLEL node.

**Function signature:**
```python
def build_parallel(
    node: dict,
    *,
    traversal_entry=None,
    compiler_context=None,
    branch_do_lists: dict | None = None,
) -> dict
```

- `branch_do_lists`: `{branch_id: list[task_dict]}` — pre-built by `dsl_generator._build_do_list()` before this function is called. The builder never computes branch content itself.
- PARALLEL is **not in `NODE_BUILDERS`** in `dsl_generator.py`. It uses a special dispatch block at the top of `generate_dsl()`'s inner loop. See `dsl_generator.md` for the dispatch pattern.

**DSL semantics:** `fork` emits parallel Zigflow/Temporal branches. `compete: false` waits for all; `compete: true` cancels all but the first to finish.

---

### `if_builder.py` — IF node

**Node data contract:**
```json
{
  "id": "N4",
  "type": "IF",
  "condition": {
    "left":     "user_email",
    "operator": "!=",
    "right":    ""
  }
}
```

- `condition` is a **root-level key** on the node (same level as `id`, `type`), not inside `data`.
- `data` is optional and omitted for simple IF nodes.
- `operator` must be one of: `==`, `!=`, `>`, `<`, `>=`, `<=`.
- `right` can be a string (`""`), a number, or a boolean.

**Task name:** `{node_id}_if`

**DSL output:**
```json
{
  "N4_if": {
    "switch": [
      { "case":    { "when": "${ $context.user_email != \"\" }", "then": "N5_greet" } },
      { "default": { "then": "N6_skip" } }
    ]
  }
}
```

- `when` expression is built by `condition_builder.build_condition_expression(node["condition"])`.
- `then` values in `case` and `default` are **task names** of the branch target nodes, pre-resolved by `traverse_graph()` via `resolve_task_name()` and stored in `traversal_entry["branch_map"]`.
- IF nodes are **never terminal** (they always have two branch targets). No `then: end` injection.

**How branching works:** Phase A (`traverse_graph()`) computes `branch_map` for each IF node:
```python
traversal_entry["branch_map"] == {
    "true":  {"node_id": "N5", "task_name": "N5_greet"},
    "false": {"node_id": "N6", "task_name": "N6_skip"},
}
```
The builder reads `traversal_entry["branch_map"]` directly. It never reads adjacency or node_map.

**Error conditions:** Raises `ValueError` if `traversal_entry` is None, if `branch_map` is missing, or if either `true` or `false` branch is missing from `branch_map`.

---

### `condition_builder.py` — Condition expression utility

Not a node builder. A leaf utility used by `if_builder.py` (and future conditional nodes).

```python
SUPPORTED_OPERATORS: frozenset[str]  # {"==", "!=", ">", "<", ">=", "<="}

def build_condition_expression(condition: dict) -> str
```

**Example outputs:**
```python
build_condition_expression({"left": "user_email",  "operator": "!=", "right": ""})
    # returns: '${ $context.user_email != "" }'

build_condition_expression({"left": "country",     "operator": "==", "right": "US"})
    # returns: '${ $context.country == "US" }'

build_condition_expression({"left": "retry_count", "operator": ">",  "right": 3})
    # returns: '${ $context.retry_count > 3 }'
```

**Type handling:** `bool` right values become `true`/`false`. `str` values are wrapped in `""`. Numeric values are rendered as-is.
**Raises `ValueError`** if `operator` is not in `SUPPORTED_OPERATORS`.
**Raises `KeyError`** if `left`, `operator`, or `right` is missing.

---

## Templates (reference only)

Files in `poc-dsl-compiler/templates/` are **not used at runtime**. They document what each active builder produces.

| Template file | Corresponding builder | Status |
|---|---|---|
| `action_input.json` | `input_builder` | ✅ matches builder output |
| `action_output.json` | `output_builder` | ✅ matches builder output |
| `action_http.json` | `action_builder` | ✅ matches builder output |
| `dsl_boilerplate.json` | `dsl_boilerplate_builder` | ✅ matches builder output |
| `wait_timer.json` | `wait_builder` (duration mode) | ✅ matches builder output |
| `wait_signal.json` | `wait_builder` (listen mode) | ✅ matches builder output |
| `if_switch.json` | `if_builder` | ✅ matches builder output |
| `action_script.json` | no builder yet | ❌ deferred |
| `action_shell.json` | no builder yet | ❌ deferred |
| `parallel.json` | `parallel_builder` | ✅ matches builder output |
| `variable.json` | no builder yet | ❌ deferred |
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
