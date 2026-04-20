# Zigflow CLI Cheatsheet

---

## 90% Daily Usage (Muscle Memory)

```bash
# Zigflow
zigflow validate workflow.yaml
zigflow run -f workflow.yaml

# Temporal
temporal workflow start --type <wf> --task-queue <q> --workflow-id id --input '{}'
temporal workflow signal --workflow-id id --name approve --input '{}'
temporal workflow show --workflow-id id
```

---

## Zigflow YAML → Temporal CLI Mapping

| Zigflow YAML | Temporal CLI flag |
|---|---|
| `workflowType` | `--type` |
| `taskQueue` | `--task-queue` |
| `listen.to.one.with.id` | `signal --name` |
| `input` (workflow start) | `--input` |

---

## Ready Patterns

```yaml
# Parallel — all branches run, output = array
fork:
  compete: false

# Race — first branch wins
fork:
  compete: true

# Wait for human approval
listen:
  to:
    one:
      with:
        id: approve
        type: signal
```

---

## Core Commands

```bash
# Validate YAML against DSL schema
zigflow validate workflow.yaml

# Start a workflow worker (polls Temporal)
zigflow run -f workflow.yaml

# Run from a directory (all YAML files)
zigflow run -f ./workflows/

# Print DSL JSON schema
zigflow schema

# Generate visual graph of a workflow
zigflow graph -f workflow.yaml

# Show Zigflow version
zigflow version
```

---

## Run Flags

```bash
# Debug logging
zigflow run -f workflow.yaml --log-level debug

# Info logging (default)
zigflow run -f workflow.yaml --log-level info

# Skip YAML validation on startup
zigflow run -f workflow.yaml --validate=false

# Custom Temporal server address
zigflow run -f workflow.yaml --temporal-address localhost:7233

# Custom Temporal namespace
zigflow run -f workflow.yaml --temporal-namespace my-namespace

# Combined
zigflow run -f workflow.yaml \
  --log-level debug \
  --temporal-address localhost:7233 \
  --temporal-namespace default
```

---

## Validate Flags

```bash
# Validate and print errors
zigflow validate workflow.yaml

# Validate all files in a directory
zigflow validate ./workflows/
```

---

## Standard Dev Flow

```bash
# Step 1 — validate
zigflow validate workflow.yaml

# Step 2 — start worker (keep running in this terminal)
zigflow run -f workflow.yaml

# Step 3 — trigger in another terminal
temporal workflow start \
  --type <workflowType> \
  --task-queue <taskQueue> \
  --workflow-id my-run-01 \
  --input '{}'

# Step 4 — send signal if workflow uses listen
temporal workflow signal \
  --workflow-id my-run-01 \
  --name approve \
  --input '{"approved": true}'

# Step 5 — inspect result
temporal workflow show --workflow-id my-run-01
```

---

## Running the Repo Examples

```bash
cd Zigflow/Examples

# hello world
zigflow validate hello_world.yaml
zigflow run -f hello_world.yaml
# trigger: temporal workflow start --type hello-world --task-queue zigflow --workflow-id hw-01 --input '{}'

# HTTP call
zigflow run -f http_call.yaml
# trigger: temporal workflow start --type fetch-user --task-queue zigflow-http --workflow-id http-01 --input '{}'

# Signal-driven
zigflow run -f signal_driven_workflow.yaml
# trigger: temporal workflow start --type signal --task-queue zigflow-signals --workflow-id sig-01 --input '{}'
# signal:  temporal workflow signal --workflow-id sig-01 --name approve --input '{"approved": true}'

# Parallel/race
zigflow run -f parallel_task.yaml
# trigger: temporal workflow start --type competing-tasks --task-queue zigflow-parallel-tasks --workflow-id par-01 --input '{}'

# Error handling
zigflow run -f error_handling.yaml
# trigger: temporal workflow start --type try-catch --task-queue zigflow-error-handle --workflow-id err-01 --input '{}'
```

---

## Debugging Checklist

```
1. zigflow validate workflow.yaml          → fix schema errors first
2. zigflow run -f workflow.yaml \
     --log-level debug                     → verbose activity/task logs
3. temporal workflow list                  → find stuck/running workflows
4. temporal workflow describe \
     --workflow-id <id>                    → check status, taskQueue, type
5. temporal workflow show \
     --workflow-id <id> --detailed         → inspect full event history
6. Check: taskQueue matches Worker config
7. Check: workflowType matches Worker config
8. Check: signal --name matches listen.to.one.with.id in YAML
```

### Failure Debugging Flow

```bash
# Step 1 — schema errors
zigflow validate workflow.yaml

# Step 2 — verbose worker output
zigflow run -f workflow.yaml --log-level debug

# Step 3 — find the workflow
temporal workflow list

# Step 4 — check its metadata
temporal workflow describe --workflow-id <id>

# Step 5 — inspect full event history
temporal workflow show --workflow-id <id> --detailed
```

---

## Common Errors

| Symptom | Fix |
|---|---|
| `schema validation failed` | Run `zigflow validate` and fix reported field |
| Worker starts but workflow never runs | `taskQueue` or `workflowType` mismatch |
| `listen` never unblocks | Signal `--name` doesn't match YAML `id` |
| `NonDeterminismError` in logs | `set` task uses non-deterministic expression |
| Workflow times out | Increase `metadata.activityOptions.startToCloseTimeout` |
