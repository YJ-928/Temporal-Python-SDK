# Decision Log

Architectural decisions for the DSL compiler. Each entry records what was decided, why, and what was rejected. This is the "why" companion to the "what" in `dsl_compiler.md` and `current_state.md`.

---

## 2026-05 — Pure function compiler

**Decision:** All compiler and builder code is pure module-level functions. No classes.

**Reason:**
- Avoids framework lock-in — pure functions need no instantiation, no lifecycle, no dependency injection
- Easier to test: call a function, inspect the return value
- Easier to read: data flows in, data flows out, no hidden state
- Easier to extend: add a file, add a function, register it

**Rejected:**
- Class registry pattern — would require instantiating builders, managing lifecycles, and creating coupling between the registry and the builder classes
- Plugin system — premature abstraction for a POC; add when there is a demonstrated need

**Accepted:**
- `NODE_BUILDERS` dispatch dict as the single dispatch mechanism
- One Python file per node type in `builders/`

---

## 2026-05 — Dispatch table, not inheritance

**Decision:** `dsl_generator.py` dispatches to builders via `NODE_BUILDERS = {"TYPE": build_fn}`. No base class, no interface, no abstract method.

**Reason:**
- Dispatch dict is explicit — you can read the entire routing at a glance
- Adding a new node type is one import + one dict entry
- No inheritance hierarchy to maintain

**Rejected:**
- Abstract base class `NodeBuilder` with `build(node)` method — adds boilerplate and coupling for no benefit in a pure-function codebase

---

## 2026-05 — Templates are documentation only

**Decision:** Files in `poc-dsl-compiler/templates/` are never imported, loaded, or executed at runtime.

**Reason:**
- Templates were created to document intended DSL output shapes before builders existed
- Rendering templates at runtime would add a dependency (Jinja2, string formatting, loading) that builders do not need
- Builders produce the DSL directly; templates serve as reference fragments

**Consequence:**
- Template and builder must stay synchronized — if they disagree, the builder is the source of truth
- Templates for deferred node types document the intended future DSL shape but have no corresponding builder yet

**Rejected:**
- Jinja2 template rendering pipeline — adds a runtime dependency for no functional gain over direct dict construction

---

## 2026-05 — Compiler owns graph, generator owns assembly

**Decision:** Hard boundary between `compiler.py` (graph pipeline) and `dsl_generator.py` (DSL assembly).

**Reason:**
- Traversal order is a graph concern; DSL shape is a schema concern
- Separating them means each can be changed independently
- Compiler does not need to know about Zigflow; generator does not need to know about graph algorithms

**Rejected:**
- Single `compile_to_dsl()` function doing both traversal and DSL construction — would grow into an unmaintainable monolith

---

## 2026-05 — WAIT node emits DSL only

**Decision:** `wait_builder.py` emits `{"wait": {"seconds": N}}` and nothing more. Timer durability, crash recovery, and execution are entirely Zigflow + Temporal runtime concerns.

**Reason:**
- Builders are serialization-only; runtime behavior is not their domain
- Documenting runtime semantics inside a builder conflates two separate concerns
- A builder author should think about DSL shape, not execution model

**Consequence:**
- Documentation (builders.md, dsl_compiler.md) uses "emits a Zigflow wait task" rather than "runs as a durable Temporal timer"
- The distinction matters: future builders (IF, PARALLEL) must follow the same principle

---

## 2026-05 — Deferred node types (IF, PARALLEL, VARIABLE, WORKFLOW)

**Decision:** V1 implements START, END, INPUT, ACTION, OUTPUT, WAIT only.

**Reason:**
- V1 goal: validate the pure-function pipeline end-to-end with a representative node set
- IF and PARALLEL require conditional/branching DSL constructs (`switch`, `fork`) that need a different traversal model
- VARIABLE is useful but not required to prove the pipeline works
- WORKFLOW (sub-workflow invocation) requires a different execution model

**Status:** Deferred until architecture expansion. Not forbidden — implement when ready, following the 11-step checklist in `dsl_compiler.md`.

---

## 2026-05 — dsl_generator is an assembler, not a builder

**Decision:** Rename mental model: `dsl_generator.py` is the **DSL assembler**, not the "master builder".

**Reason:**
- "Master builder" implies it builds DSL content — it does not; individual builders do
- "Assembler" accurately describes its role: receive traversal, call builders, compose the final document
- The distinction prevents future agents from adding DSL fragment logic into `dsl_generator.py`

**Rule enforced:** `dsl_generator.py` must never contain node-specific DSL construction. If it does, extract to a builder.

---

## 2026-05 — Compiler does not validate generator output

**Decision:** The compiler assumes workflow JSON produced by the generator is structurally valid. It does not explicitly validate graph constraints before traversal.

**Reason:**
- Generator enforces constraints (one START, one END, no orphan nodes) during generation
- Adding validation in the compiler would duplicate logic and slow the pipeline
- V1 is a POC; explicit validation is a V2 concern

**Risk:** Violations in the input JSON cause undefined traversal behavior (silent errors or wrong DSL), not explicit errors.

**Consequence:** Explicit input validation should be added before the compiler is used with untrusted input (e.g., arbitrary user-submitted JSON from a UI).
