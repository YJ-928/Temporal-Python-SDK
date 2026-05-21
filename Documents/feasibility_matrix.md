# Feasibility Matrix

> **Status:** R&D / Design Phase
> **Purpose:** Evaluate the technical feasibility of every major component, library choice, and integration point. Identifies build risk, unknown dependencies, and go/no-go signals before any implementation begins.

---

## 1. Overview

This document answers: **Can we actually build this?** It does not assume feasibility — it actively looks for blockers.

Risk levels:
- **GREEN** — well-understood, low risk, proven in this repo or widely documented
- **YELLOW** — some unknowns, requires a spike/POC to confirm, medium risk
- **RED** — significant unknown or hard dependency on undocumented system, high risk

---

## 2. Core Library Feasibility

### 2.1 Pydantic V2

| Factor | Assessment | Risk |
|---|---|---|
| Used for graph input validation (`WorkflowGraph`, `Node`, `Edge` schema) | pydantic v2 is a transitive dependency of fastapi — already available | GREEN |
| V1 vs V2 API differences | V2 uses `model_validator`, `field_validator`, `model_config`. V1 uses `@validator`, `Config` class. Mixing them causes runtime errors. | YELLOW |
| Performance at large graph size (100+ nodes) | pydantic v2 is Rust-backed; validation of a 100-node graph should complete in <10ms | GREEN |
| JSON serialization of nested dataclasses | `model.model_dump(mode="json")` handles nested models | GREEN |
| Unknown: discriminated unions for Node/Edge subtypes | Pydantic v2 discriminated unions on `Literal` types work for `node_type` fields. Requires each node type to be a separate Pydantic model. This is a design decision (one giant `Node` model vs per-type models). | YELLOW |

**Verdict:** GREEN. Use pydantic v2 throughout. Use a single `Node` model with `config: dict` rather than per-type submodels for V1 to avoid complexity.

---

### 2.2 SQLAlchemy Async + aiosqlite

| Factor | Assessment | Risk |
|---|---|---|
| Async engine setup | `create_async_engine("sqlite+aiosqlite:///./db.sqlite3")` — standard pattern | GREEN |
| SQLite WAL mode for concurrent reads during compilation | Set via `engine.execute("PRAGMA journal_mode=WAL")` on first connect | GREEN |
| JSONB column for graph storage | SQLite has no native JSONB type. SQLAlchemy `JSON` type serializes to TEXT. Query performance on large JSON blobs is acceptable for V1 (no JSON path queries needed). | GREEN |
| Alembic migrations | Standard SQLAlchemy + Alembic migration setup; 4 tables (workflows, workflow_versions, executions, templates) | GREEN |
| Thread safety in async context | aiosqlite wraps sqlite3 in an asyncio event loop. Do not mix sync sqlite3 calls in async routes. | YELLOW |
| Unknown: concurrent write conflicts | SQLite supports only one writer at a time. If multiple compilation requests arrive simultaneously, they queue. For V1 this is acceptable. | GREEN (V1 scope) |

**Verdict:** GREEN for V1. Single-writer SQLite is acceptable. If V2 requires concurrent compilation, migrate to PostgreSQL with `asyncpg`.

---

### 2.3 ruamel.yaml

| Factor | Assessment | Risk |
|---|---|---|
| Preserves block style vs flow style | ruamel.yaml emits block style by default; PyYAML collapses lists to flow style. Zigflow YAML files should be block-style for readability. | GREEN (ruamel wins) |
| Comments in output | ruamel.yaml can emit YAML comments; useful for generated file headers. | GREEN |
| Parsing order-preserved dicts | ruamel.yaml preserves key insertion order in `CommentedMap`. Zigflow YAML must preserve `document`, `use`, `do` ordering. | GREEN |
| Unknown: ruamel.yaml version API stability | ruamel.yaml has had API-breaking releases between 0.16 and 0.18. Must pin to a specific minor version. | YELLOW |
| Unknown: ruamel.yaml quoting behavior | For Zigflow expression strings like `"${ .user.name }"`, ruamel.yaml must quote these strings (they start with `$` which is not a special YAML character, but to be safe). Must verify quoting behavior with `${ }` prefixed values. | YELLOW |

**Verdict:** YELLOW. Use ruamel.yaml, but write a single-function test that serializes a `${ }` expression to YAML and confirms the output is valid Zigflow YAML (i.e., `zigflow validate` passes). This is a required spike before generator implementation.

---

### 2.4 Zigflow CLI Dependency

| Factor | Assessment | Risk |
|---|---|---|
| zigflow CLI availability | Must be installed in the execution environment. Not a Python package — installed separately. | YELLOW |
| Version pinning | No official semantic versioning guarantee observed. Must pin by commit SHA or release tag if using in CI. | YELLOW |
| `zigflow validate` exit codes | Assumes exit code 0 = valid, non-zero = invalid. Must verify — if zigflow uses different exit codes, the API's validation endpoint breaks. | RED |
| `zigflow run -f <file>` startup time | Unknown. If it takes >5 seconds to start the Zigflow worker, the execution bridge needs an async health-check loop. | RED |
| `zigflow run` signal handling | Does `zigflow run` respond to SIGTERM? If the execution bridge kills the process, does the Zigflow worker clean up gracefully? | RED |
| `zigflow validate` output format | Is it human-readable text or JSON? If text, parsing error messages for the API response requires string parsing, which is fragile. | YELLOW |
| Zigflow worker registration of workflow types | `zigflow run -f workflow.yaml` registers the `workflowType` from the YAML. Does it also register sub-workflow types? Must verify for WORKFLOW node support. | YELLOW |

**Verdict:** RED for the execution bridge. There are 3 red-flagged unknowns about the Zigflow CLI. These must be resolved empirically before any execution bridge code is written. For the compiler (Validator, Normalizer, IR, Planner, Generator), this risk is irrelevant — compilation has no dependency on the Zigflow CLI.

**Resolution plan:**
1. Run `zigflow validate examples/hello_world.yaml` and observe exit code and stdout/stderr format
2. Run `zigflow run -f examples/hello_world.yaml` and measure startup time (time until "worker ready" or equivalent)
3. Send SIGTERM to the worker and observe shutdown behavior
4. Document findings in `poc_scope.md`

---

### 2.5 Temporal Python SDK (for Execution Bridge)

| Factor | Assessment | Risk |
|---|---|---|
| `Client.connect()` to localhost:7233 | Standard pattern — used throughout this repo | GREEN |
| `client.start_workflow()` after Zigflow worker is running | The Zigflow worker must be running and the workflow type registered before `start_workflow` is called. Race condition if `start_workflow` is called too early. | YELLOW |
| Polling workflow result with `handle.result()` | Standard pattern. Will block indefinitely on long-running workflows. For the API, must use `asyncio.wait_for(handle.result(), timeout=N)` or return immediately and poll separately. | YELLOW |
| `handle.signal()` for Zigflow signal tasks | Signal name must exactly match the `listen.to.one.with.id` in the YAML. The API must accept signal name from the user. | GREEN |
| `handle.query()` for workflow state | Only available if the Zigflow worker registers a query handler. Zigflow may not expose query handlers in V1. | RED |
| Workflow ID uniqueness | Must be enforced by the API — two simultaneous runs of the same workflow with the same ID will fail at Temporal. | GREEN (simple UUID) |

**Verdict:** YELLOW for execution bridge Temporal integration. The critical unknown is whether Zigflow registers query handlers. If not, there is no way to observe running workflow state via the Temporal SDK — only the Web UI shows state.

---

## 3. Compiler Stage Feasibility

| Stage | Core Algorithm | Complexity | Risk |
|---|---|---|---|
| Validator | Kahn's topological sort + BFS reachability | O(V + E) — trivial for graphs < 1000 nodes | GREEN |
| Normalizer | Per-edge type inference + per-node config merge | O(N * C) where C = config fields per node | GREEN |
| IR Builder | Recursive subtree walk + convergence point detection | O(V²) in worst case (convergence scan per node) | YELLOW |
| Planner | Single pass over IR tasks with annotation rules | O(T) where T = IR task count | GREEN |
| Generator | Template lookup + recursive rendering + YAML serialization | O(T * L) where L = template length | GREEN |

**IR Builder convergence point detection is the highest-complexity step.** For typical graphs (5–20 nodes), this is negligible. For large graphs (100+ nodes with deeply nested IF/PARALLEL), the O(V²) convergence scan could be slow. An optimization (memoize reachability sets) brings this to O(V + E) but adds implementation complexity.

**V1 recommendation:** Implement the naive O(V²) algorithm. Profile with a 50-node graph. Optimize only if profiling shows a problem.

---

## 4. Zigflow DSL Unknowns (Critical for Generator)

These are design-blocking unknowns that require empirical verification before the Generator can be finalized.

| Unknown | Impact | How to Resolve |
|---|---|---|
| `switch` task structure (Structure A: inline `do` vs Structure B: task jump references) | Major — changes IR nesting model and Generator algorithm | Build a 3-node IF graph, generate both DSL variants, run `zigflow validate` on both, run `zigflow run` on both |
| `fork` task branch result shape with `compete: false` | Medium — changes how Generator emits `output.as` for PARALLEL | Test with `parallel_task.yaml` from `Zigflow/Yaml/` — inspect Temporal Web UI event history for result payload |
| `run: workflow` DSL structure for child sub-workflows | Medium — needed for WORKFLOW node (child type) generator | Check Zigflow Docs/source for `run.workflow` spec; test with `Docker/long_running_workflow/workflow.json` |
| Zigflow expression context after `fork` (does `$data` contain all branch results or just the last?) | Medium — affects how PARALLEL nodes expose results to subsequent tasks | Empirical test: parallel two `set` tasks, access `$data` in next task |
| Zigflow `listen` task timeout behavior (does WAIT with signal type support a deadline?) | Low — affects WAIT node's signal mode for deadline-based waits | Test: add `timeout` to a `listen` task and validate |

---

## 5. Build vs Buy Analysis

### Graph Validation

| Option | Notes | Verdict |
|---|---|---|
| Build custom validator (proposed) | Full control over error codes and messages. No external dependency. ~200 lines of code. | **BUILD** — simple enough |
| NetworkX (Python graph library) | Has built-in cycle detection and topological sort. But adds a non-trivial dependency and wraps the graph in a different model. | PASS for V1 — don't add the dependency |
| JSON Schema only | Only validates structure, not semantics (e.g., cannot check "IF must have exactly two branch edges"). | INSUFFICIENT — don't use alone |

### Template Engine

| Option | Notes | Verdict |
|---|---|---|
| Jinja2 | Available, powerful, but YAML + Jinja2 = whitespace headaches | AVOID for YAML generation |
| Python dict builder | Verbose but correct | **BUILD (V1)** |
| ruamel.yaml object model | Clean, YAML-native | **USE for serialization** |
| Handlebars/Mustache (via PyYaml-template) | Too niche, no clear Python package | PASS |

### Graph Storage

| Option | Notes | Verdict |
|---|---|---|
| SQLite + JSON column | Sufficient for V1 (no graph queries needed) | **USE (V1)** |
| PostgreSQL JSONB | Supports JSON path queries — useful for searching workflow graphs | Defer to V2 |
| Graph DB (Neo4j, ArangoDB) | Supports graph traversal queries natively | Over-engineered for V1 scope |

---

## 6. Performance Risk Analysis

| Scenario | Expected Behavior | Risk |
|---|---|---|
| Compiling a 5-node graph | < 50ms total pipeline | GREEN |
| Compiling a 50-node graph with nested IF/PARALLEL | < 500ms — IR Builder convergence scan is the bottleneck | YELLOW |
| Compiling a 200-node graph | Could exceed 2s — convergence scan is O(V²) = 40,000 iterations | YELLOW — optimize if needed |
| Storing a 200-node graph JSON to SQLite | JSON blob ~50KB — negligible for SQLite | GREEN |
| Running 10 simultaneous compilation requests | SQLite write queue — requests serialize. P99 latency = 10 × 500ms = 5s for 50-node graphs | YELLOW (V1 acceptable) |
| Zigflow worker startup time × 10 simultaneous execution requests | Unknown (see Section 2.4 RED items) | RED |

---

## 7. Testing Strategy Feasibility

| Test type | Feasibility | Notes |
|---|---|---|
| Validator unit tests (graph fixtures → ValidationResult) | GREEN — pure function, no I/O | 15–20 test cases covering each error code |
| Normalizer unit tests (raw graph → normalized graph) | GREEN — pure function | 10 test cases covering handle inference, default filling |
| IR Builder unit tests (normalized graph → IR) | GREEN — pure function | Complex: needs 5+ graph fixtures including IF/PARALLEL/WAIT |
| Generator unit tests (IR → YAML string) | YELLOW — must assert YAML string structure without full `zigflow validate` | Use pyyaml to parse the output and assert structure |
| Generator integration tests (IR → YAML → zigflow validate passes) | YELLOW — requires zigflow CLI installed in test environment | Run in Docker or skip in pure unit test CI |
| End-to-end test (graph JSON → compile → run → Temporal result) | RED — requires Temporal dev server + zigflow worker running | Only for manual testing; not in automated CI for V1 |

---

## 8. Dependency Version Risk

| Dependency | Version constraint | Risk |
|---|---|---|
| `temporalio` | `>=1.24.0` (from pyproject.toml) | GREEN — pinned in repo |
| `fastapi` | `>=0.135.2` | GREEN — pinned |
| `uvicorn` | `>=0.42.0` | GREEN |
| `aiohttp` | `>=3.13.5` | GREEN |
| `aiosqlite` | Not currently in pyproject.toml — must add | YELLOW — add explicitly |
| `sqlalchemy` | Not currently in pyproject.toml — must add with async extras | YELLOW — add explicitly |
| `alembic` | Not currently in pyproject.toml — must add | YELLOW |
| `ruamel.yaml` | Not currently in pyproject.toml — must add, pin minor version | YELLOW |
| `zigflow` CLI | Not a Python package — external install | RED — version pinning strategy undefined |

---

## 9. Feasibility Summary

| Component | Feasibility | Blocking Unknowns | POC needed? |
|---|---|---|---|
| Graph schema (pydantic models) | GREEN | None | No |
| Validator pipeline stage | GREEN | None | No |
| Normalizer pipeline stage | GREEN | None | No |
| IR Builder pipeline stage | YELLOW | Convergence point algorithm needs testing | Yes (unit tests) |
| Planner pipeline stage | GREEN | None | No |
| Generator: ACTION, VARIABLE, WAIT | YELLOW | ruamel.yaml `${ }` quoting behavior | Yes (ruamel spike) |
| Generator: IF/switch | RED | Zigflow switch DSL structure unknown | Yes (POC: zigflow validate) |
| Generator: PARALLEL/fork | YELLOW | fork branch result shape unknown | Yes (POC: zigflow run) |
| Generator: WORKFLOW/child | YELLOW | `run: workflow` DSL structure unknown | Yes (check docs/source) |
| Storage (SQLite + SQLAlchemy async) | GREEN | None | No |
| REST API (FastAPI routes) | GREEN | None | No |
| Execution bridge (subprocess zigflow) | RED | Exit codes, startup time, SIGTERM behavior | Yes (empirical test) |
| Temporal SDK for execution bridge | YELLOW | Query handler availability in Zigflow | Yes (empirical test) |

**Overall V1 feasibility:** YELLOW. The compiler (all 5 stages) is feasible. The execution bridge has multiple RED unknowns that must be resolved before implementation. **The recommended path is to build and validate the compiler first (POC scope), then tackle the execution bridge as a separate phase.**
