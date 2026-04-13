# Temporal Workflow Concepts - Practical Guide (File Processing System)

## Example Context

We are building a **long-running File Processor Workflow**:

* A single workflow receives **file IDs via signals**
* Each signal triggers **parallel file processing**
* Activities process files using available workers
* Supports scaling, retries, monitoring, and control

---

# 1. Workflow Fundamentals

## Loops inside Temporal

* Supported using `while` loops inside workflow
* Used for:

  * Long-running systems
  * Polling / waiting for signals
* Example:

  * Workflow waits indefinitely and processes incoming file signals

---

## Long-Term vs Short-Term Jobs

### Long-Running Workflows

* Duration: minutes → years
* Example:

  * File processor waiting for signals continuously
* Temporal behavior:

  * Sleeps (no CPU usage)
  * Resumes on events (signals/timers)

### Short-Term Workflows

* Duration: seconds → minutes
* Example:

  * Process a single file and exit

---

## Definition

| Type          | Definition                                |
| ------------- | ----------------------------------------- |
| Long-running  | Stateful, event-driven, survives failures |
| Short-running | Immediate execution, quick completion     |

---

# 2. Retries

* Built-in via `RetryPolicy`
* Used for:

  * Network failures
  * Temporary issues

Not for business loops

Example:

* File processing activity retries if file read fails

---

# 3. Fork & Merge (Parallel Execution)

## Fork

* Start multiple activities in parallel
* Example:

  * 20 files → 20 activities

## Merge

* Wait for all to complete
* Example:

  * Collect all processed file results

---

# 4. Core Workflow Pipeline

## Triggers (Workflow Start)

Possible triggers:

* API call
* Scheduler (cron)
* User action
* Event/message

Example:

* User uploads files → starts workflow

---

## Data Capture

Sources:

* Forms
* Files (your case)
* API input

---

## Validation

* Validate file format
* Check file size/type

---

## Enrichment

* Add metadata
* Extract file info

---

## Decision & Routing

* Route based on:

  * File type
  * Priority
  * Size

---

## Human Interaction (HITL)

* Pause workflow for approval
* Example:

  * Manual validation before processing sensitive files

---

## Execution

* Activities:

  * Process file
  * Store results
  * Call external APIs

---

## Sequential vs Parallel

| Type       | Example                         |
| ---------- | ------------------------------- |
| Sequential | Validate → process → store      |
| Parallel   | Process 20 files simultaneously |

---

# 5. Monitoring & Observability

## SLA Tracking

* Define time per step
* Example:

  * File must process within 10 seconds

## Monitoring

* Temporal Web UI
* Logs
* Metrics

---

## Auditing & Logging (Critical)

* Event history tracks:

  * Signals
  * Activities
  * State changes

* Logs:

  * `workflow.logger`
  * `activity.logger`

---

# 6. Common Workflow Attributes

## Stateful Workflow

* Maintains:

  * processed files
  * pending tasks

---

## Deterministic vs Non-Deterministic

| Type              | Rule                  |
| ----------------- | --------------------- |
| Deterministic     | Required in workflows |
| Non-deterministic | Allowed in activities |

---

# 7. Enterprise Capabilities

## Policy Enforcement

* Role-based execution
* Access control

---

## Exception Handling

* Activity retries
* Workflow failure handling

---

## Versioning

* Update workflow safely without breaking running executions

---

## Resilience

* Survives:

  * crashes
  * restarts
  * network issues

---

## Traceability

* Full event history replay

---

## Controllability

Supported controls:

* Pause
* Resume
* Override (signals)
* Stop workflow
* Kill switch

---

# 8. Performance & Scaling

## Throughput

* Files processed per day

---

## Scaling

* Add more workers
* Temporal distributes tasks automatically

---

## Queuing

* Task Queue holds pending activities

---

## SLA

* Defines expected completion time

---

## Idempotency

* Activities should be safe to retry

---

## Impact Levels

| Type | Example            |
| ---- | ------------------ |
| Low  | Image processing   |
| High | Payment processing |

---

# 9. Execution Modes

## Sync vs Async

| Type  | Description       |
| ----- | ----------------- |
| Sync  | Wait for result   |
| Async | Fire and continue |

---

## Batch Execution

* Process multiple files together

---

## Real-Time Execution

* Process immediately on signal

---

# 10. Parallel File Processing (Your Core Use Case)

## Architecture

```text
FileProcessorWorkflow (long-running)
        ↓ (signal)
start_activity(file_id)
        ↓
Workers process files in parallel
```

---

## Behavior

* 20 signals received
* 10 workers available

```text
10 files processed immediately
10 files queued
```

---

## Key Concept

```text
Signals = sequential triggers
Activities = parallel execution
```

---

## Best Practice

* Use:

  * `workflow.start_activity()` (non-blocking)
* Avoid:

  * `await execute_activity()` inside signal

---

# 11. Advanced Patterns

## Continue-As-New

* Reset workflow history for long-running workflows

---

## Child Workflows

* One workflow per file (scalable design)

---

## Fan-out / Fan-in

* Parallel execution + aggregation

---

# Final Summary

Temporal enables:

* Long-running, stateful workflows
* Parallel processing via activities/workers
* Reliable retries and execution
* Full observability and auditability
* Scalable file processing pipelines

---

## Golden Rule

```text
Workflow = Orchestrator (single-threaded)
Activities & Workers = Parallel execution engine
```

---

## Use Case Verdict

✔ Single workflow handling multiple files → Possible
✔ Parallel processing → Achieved via activities
✔ Scaling → Add workers
✔ Reliability → Built-in

---