# POC Scope

> **Status:** R&D / Design Phase
> **Purpose:** Defines the minimum viable POC that validates the core architecture. Specifies what is included, what is explicitly excluded, success criteria, and a step-by-step build order.

---

## 1. POC Objective

Validate the single most uncertain part of the architecture: **can the compiler pipeline transform a valid WorkflowGraph JSON into a Zigflow YAML that passes `zigflow validate` and executes correctly with `zigflow run`?**

Everything else — the API, storage, UI, execution bridge, normalizer defaults, registry files — is excluded from the POC.

---

## 2. POC Success Criteria

The POC is considered successful when all of the following are true:

| # | Criterion | How to verify |
|---|---|---|
| 1 | A hand-crafted `WorkflowGraph` JSON is accepted by the Validator with 0 errors | Unit test: `validate(graph)` returns `valid: true` |
| 2 | The Validator correctly rejects a graph missing a START node | Unit test: `validate(broken_graph)` returns `MISSING_START` |
| 3 | The IR Builder produces a correct `WorkflowIR` from the normalized graph | Unit test: assert IR task names, order, and branch structure |
| 4 | The Generator produces a valid YAML string from the IR | `zigflow validate generated.yaml` exits with code 0 |
| 5 | The generated workflow runs to completion on a live Temporal dev server | `zigflow run -f generated.yaml` + `temporal workflow start` succeeds |
| 6 | The generated workflow handles the IF branch correctly at runtime | Run with two different inputs; observe different branch execution in Temporal Web UI |

Criteria 1–3 are achievable with pure unit tests (no Zigflow CLI required). Criteria 4–6 require a live environment.

---

## 3. POC Graph: Conditional HTTP Fetch

The POC graph has 5 nodes and 4 edges. It is the smallest graph that exercises:
- Sequential ACTION execution
- IF branching (two paths)
- Variable assignment on each branch
- A single convergence to END

```
START → ACTION(http) → IF(condition) → VARIABLE(active_user) → END
                                      ↘ VARIABLE(inactive_user) → END
```

### Nodes

```json
{
  "nodes": [
    {
      "id": "n-start",
      "type": "START",
      "label": "Start",
      "position": { "x": 0, "y": 0 },
      "config": {},
      "inputs": [],
      "outputs": [{ "id": "output", "label": "output" }]
    },
    {
      "id": "n-fetch",
      "type": "ACTION",
      "label": "Fetch User",
      "position": { "x": 200, "y": 0 },
      "config": {
        "protocol": "http",
        "method": "get",
        "endpoint": "https://jsonplaceholder.typicode.com/users/1",
        "outputKey": "user"
      },
      "inputs": [{ "id": "input", "label": "input" }],
      "outputs": [
        { "id": "success", "label": "success" },
        { "id": "error", "label": "error" }
      ]
    },
    {
      "id": "n-if",
      "type": "IF",
      "label": "Is Active",
      "position": { "x": 400, "y": 0 },
      "config": {
        "condition": "${ $context.user.active == true }"
      },
      "inputs": [{ "id": "input", "label": "input" }],
      "outputs": [
        { "id": "true", "label": "true" },
        { "id": "false", "label": "false" }
      ]
    },
    {
      "id": "n-active",
      "type": "VARIABLE",
      "label": "Mark Active",
      "position": { "x": 600, "y": -100 },
      "config": {
        "assignments": { "status": "active" },
        "outputKey": "result"
      },
      "inputs": [{ "id": "input", "label": "input" }],
      "outputs": [{ "id": "success", "label": "success" }]
    },
    {
      "id": "n-inactive",
      "type": "VARIABLE",
      "label": "Mark Inactive",
      "position": { "x": 600, "y": 100 },
      "config": {
        "assignments": { "status": "inactive" },
        "outputKey": "result"
      },
      "inputs": [{ "id": "input", "label": "input" }],
      "outputs": [{ "id": "success", "label": "success" }]
    },
    {
      "id": "n-end",
      "type": "END",
      "label": "End",
      "position": { "x": 800, "y": 0 },
      "config": {},
      "inputs": [{ "id": "input", "label": "input" }],
      "outputs": []
    }
  ]
}
```

### Edges

```json
{
  "edges": [
    { "id": "e1", "source": "n-start", "target": "n-fetch", "edge_type": "DEFAULT" },
    { "id": "e2", "source": "n-fetch", "target": "n-if", "edge_type": "SUCCESS" },
    { "id": "e3", "source": "n-if", "target": "n-active", "edge_type": "TRUE" },
    { "id": "e4", "source": "n-if", "target": "n-inactive", "edge_type": "FALSE" },
    { "id": "e5", "source": "n-active", "target": "n-end", "edge_type": "SUCCESS" },
    { "id": "e6", "source": "n-inactive", "target": "n-end", "edge_type": "SUCCESS" }
  ]
}
```

### Expected Generator Output

Note: this is what the Generator should produce. The IF/switch structure shown here uses assumed Structure A — this is what criterion 4 validates (does `zigflow validate` accept it?).

```yaml
document:
  dsl: "1.0.0"
  taskQueue: "poc-queue"
  workflowType: "conditional-fetch"
  version: "1.0.0"

do:
  - fetch_user:
      call: http
      with:
        method: get
        endpoint: "https://jsonplaceholder.typicode.com/users/1"
      export:
        as: "${ $context + { user: . } }"

  - is_active:
      switch:
        - when: "${ $context.user.active == true }"
          then:
            do:
              - mark_active:
                  set:
                    status: "active"
                  export:
                    as: "${ $context + { result: { status: \"active\" } } }"
        - then:
            do:
              - mark_inactive:
                  set:
                    status: "inactive"
                  export:
                    as: "${ $context + { result: { status: \"inactive\" } } }"
```

---

## 4. What Is Excluded from the POC

The following are explicitly OUT of POC scope. Building them before criteria 1–6 are met is premature.

| Excluded | Reason |
|---|---|
| REST API (FastAPI routes) | No user interface needed to test the compiler pipeline |
| Database (SQLite, SQLAlchemy, Alembic) | No persistence needed to test compilation |
| Normalizer default-filling | Use explicit config values in POC graph (no defaults needed) |
| Registry YAML files | Hard-code dispatch rules in the Generator for the 3 node types in the POC |
| Planner (`ExecutionPlan` output) | Not needed to validate YAML generation |
| Execution bridge (subprocess zigflow) | zigflow CLI is invoked manually in the POC |
| PARALLEL node (fork) | Complex — defer until IF is verified |
| WAIT node | Defer until basic compilation is verified |
| WORKFLOW node (child/external) | Defer — depends on verified `run: workflow` DSL structure |
| LOOP edge handling | V1 raises error; defer |
| Template engine (YAML blueprints) | Use Python dict builder for POC |
| Error edge routing | Advisory-only in POC; no try/catch wrapping |
| UI / frontend | Not in scope for any phase of docs-only R&D |

---

## 5. Step-by-Step POC Build Order

### Step 0: Environment Preparation

Before writing any code:
1. Verify `zigflow` CLI is installed: `zigflow --version`
2. Verify `temporal server start-dev` is running: open `http://localhost:8233`
3. Verify the existing `Zigflow/Yaml/` examples work: `zigflow validate Zigflow/Yaml/hello_world.yaml`
4. Test `zigflow validate` exit code: `zigflow validate Zigflow/Yaml/hello_world.yaml; echo "Exit: $?"`
5. Document exit codes and error format before writing the Validator stage

### Step 1: Validate the switch DSL structure

Before writing the IR Builder or Generator:
1. Manually write `poc/switch_test_a.yaml` using assumed Structure A (inline `do`)
2. Run `zigflow validate poc/switch_test_a.yaml`
3. If it fails, manually write `poc/switch_test_b.yaml` using Structure B (task reference)
4. Run `zigflow validate poc/switch_test_b.yaml`
5. Record which structure is valid — this determines the Generator algorithm

**This is a prerequisite gate.** Do not start Generator implementation until step 1 is complete.

### Step 2: Build the Validator (Stage 1)

- Implement the 14 validation rules from `compiler_design.md` Section 2
- Write unit tests for each error code (14 test cases minimum)
- Input: raw Python dict matching `WorkflowGraph` schema
- Output: `{"valid": bool, "errors": [...]}`
- No external dependencies — pure Python

### Step 3: Build the IR Builder (Stage 3, skipping Normalizer)

- Skip the Normalizer for the POC — use an already-normalized graph (explicit handle IDs, explicit config values)
- Implement the topological walk algorithm from `compiler_design.md` Section 4
- Implement convergence point detection for the IF node case
- Write 3 unit tests: linear graph, IF graph, IF graph with both branches going to END (no convergence)
- Output: Python dict matching `WorkflowIR` schema

### Step 4: Build the Generator (Stage 5, skipping Planner)

- Implement template dispatch for 3 node types: ACTION (http), IF, VARIABLE
- Use Python dict builder (no Jinja2, no YAML blueprints)
- Use ruamel.yaml for serialization
- Test ruamel.yaml `${ }` expression quoting behavior first (spike from `feasibility_matrix.md` Section 2.3)
- Output: YAML string

### Step 5: Validate the Generated YAML

- Write the generated YAML string to a temp file: `poc/generated_poc.yaml`
- Run: `zigflow validate poc/generated_poc.yaml`
- If validation fails: inspect the error, fix the Generator, re-run
- This is criterion 4

### Step 6: Run the Generated Workflow

- Start the Zigflow worker: `zigflow run -f poc/generated_poc.yaml`
- Trigger the workflow: `temporal workflow start --type conditional-fetch --task-queue poc-queue --workflow-id poc-run-01 --input '{}'`
- Observe in Temporal Web UI at `http://localhost:8233`
- Verify completion: `temporal workflow show --workflow-id poc-run-01`
- This is criterion 5 and 6

---

## 6. POC Go / No-Go Decision Criteria

After completing all 6 steps, evaluate:

| Signal | Go (proceed to full impl) | No-Go (redesign needed) |
|---|---|---|
| Validator | All 14 unit tests pass | Any test fails — fix rules before proceeding |
| IR Builder | IF convergence detection produces correct branch grouping | Convergence algorithm produces incorrect nesting → reconsider algorithm |
| Generator | `zigflow validate` exits with code 0 | Validation fails → one of the switch DSL structures must be wrong → re-test both |
| Execution | Workflow completes in Temporal Web UI | Workflow fails at Temporal level → inspect event history for error |
| IF branching | Both branches execute correctly with different inputs | Only one branch works → switch task semantics differ from assumption |

**No-Go scenarios and their implications:**

1. **`zigflow validate` rejects both switch DSL structures:** The switch task may not exist in the Zigflow version installed, or the syntax is fundamentally different. Read the Zigflow worker source code or official changelog. Full redesign of IF node generator required.

2. **Convergence detection produces wrong output for 3-branch graphs:** The algorithm needs a domain model change. The entire IR Builder may need a different data structure (e.g., dominator tree instead of naive set intersection).

3. **ruamel.yaml serializes `${ }` expressions incorrectly:** Fall back to PyYAML with explicit string quoting, or build a custom serializer. Minor risk — solvable.

4. **Zigflow worker exits immediately after starting:** CLI flag or environment misconfiguration. Not a design risk — operational issue.

---

## 7. What Success Unlocks

A successful POC (all 6 criteria met) means:

| Phase | Unlocked by |
|---|---|
| Normalizer implementation | Criteria 1–3 (Validator and IR Builder verified) |
| Full node type coverage (PARALLEL, WAIT, WORKFLOW) | Criteria 4–5 (Generator and runtime verified) |
| Registry YAML files | Criteria 4 (Generator structure confirmed) |
| REST API (FastAPI routes) | Criteria 1–3 (compiler pipeline verified) |
| Database storage | Criteria 1–3 (schema stable) |
| Execution bridge | Criteria 4–6 + empirical Zigflow CLI exit code and startup time data |

**The POC is the prerequisite for all other implementation phases.** Nothing in `workflow_builder_architecture.md` should be implemented before the POC is complete and all 6 criteria are met.

---

## 8. POC File Structure

The POC creates files only inside `Zigflow-DSL-Compiler/poc/` (not mixed into the production package). All POC files are throwaway.

```
Zigflow-DSL-Compiler/
  poc/
    switch_test_a.yaml        # Manually crafted — switch Structure A
    switch_test_b.yaml        # Manually crafted — switch Structure B
    poc_graph.json            # The 5-node POC graph from Section 3
    generated_poc.yaml        # Output of the Generator (written by hand first, then by Generator)
    test_validator.py         # Unit tests for Stage 1
    test_ir_builder.py        # Unit tests for Stage 3
    test_generator.py         # Unit tests for Stage 5
    compiler_poc.py           # Minimal main() that wires all 3 stages
```

These files are NOT part of the production codebase. They are used to validate assumptions. Once POC criteria are met, the production compiler is implemented in the main package structure.

---

## 9. Timeline Consideration (Effort, Not Calendar Time)

| POC Step | Effort estimate | Notes |
|---|---|---|
| Step 0: Environment prep | Small | Mostly verification — no code |
| Step 1: Switch DSL validation | Small | Manually write 2 YAML files and test |
| Step 2: Validator | Medium | 14 rules + 14 unit tests |
| Step 3: IR Builder | Large | Convergence algorithm is the hardest part |
| Step 4: Generator | Medium | 3 node types; ruamel.yaml spike first |
| Step 5: YAML validation | Small | Run `zigflow validate`; fix if needed |
| Step 6: Live execution | Small | Run and observe |

**Largest risk item:** Step 3 (IR Builder convergence). Plan to spend extra time here. If convergence detection is not correct, it will cascade into Generator failures.
