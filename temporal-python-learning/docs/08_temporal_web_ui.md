# Temporal Web UI

## Overview

The Temporal Web UI provides a graphical interface to observe and manage Workflow executions. It is available at `http://localhost:8233` when running the Temporal dev server.

## Accessing the Web UI

```bash
# Start the dev server (includes Web UI)
temporal server start-dev
```

Open `http://localhost:8233` in your browser.

## Web UI Sections

### 1. Workflow List

The main page shows all Workflow executions:

```
┌────────────────────────────────────────────────────────┐
│  Workflows                                              │
├─────────────┬──────────┬───────────┬──────────────────┤
│ Workflow ID │ Type     │ Status    │ Start Time       │
├─────────────┼──────────┼───────────┼──────────────────┤
│ greeting-1  │ GreetSo..│ Completed │ 2024-01-15 10:30 │
│ pizza-ord-1 │ PizzaOr..│ Running   │ 2024-01-15 10:29 │
└─────────────┴──────────┴───────────┴──────────────────┘
```

### 2. Workflow Details

Click a Workflow to see:
- **Summary**: ID, type, status, run ID
- **Input**: The parameters passed to the Workflow
- **Output**: The result (if completed)
- **Pending Activities**: Activities currently executing

### 3. Event History

The event history shows every step of Workflow execution:

```
1. WorkflowExecutionStarted
2. WorkflowTaskScheduled
3. WorkflowTaskStarted
4. WorkflowTaskCompleted
5. ActivityTaskScheduled
6. ActivityTaskStarted
7. ActivityTaskCompleted
8. WorkflowExecutionCompleted
```

Each event is expandable to show:
- **Timestamp**
- **Event attributes** (input, output, timeouts)
- **Stack trace** (for failures)

### 4. Workflow Status Types

| Status | Description |
|--------|-------------|
| Running | Workflow is currently executing |
| Completed | Workflow finished successfully |
| Failed | Workflow terminated with an error |
| Timed Out | Workflow exceeded its timeout |
| Cancelled | Workflow was manually cancelled |
| Terminated | Workflow was forcefully terminated |

## Using the Web UI for Debugging

### Inspecting Failed Workflows

1. Filter Workflows by status: **Failed**
2. Click the failed Workflow
3. Examine the event history — look for `ActivityTaskFailed` events
4. Expand the event to see the error message and stack trace

### Inspecting Activity Results

1. Open a Workflow's event history
2. Find `ActivityTaskCompleted` events
3. Expand to see the Activity's return value

### Inspecting Timers

1. Look for `TimerStarted` and `TimerFired` events
2. Check the timer duration in the event attributes

## Web UI Architecture

```
Browser ──► Web UI (port 8233)
                    │
                    ▼
            Temporal Server (port 7233)
                    │
                    ▼
              Event History DB
```

## Best Practices

- Use the Web UI as your primary debugging tool during development
- Filter Workflows by status to find failures quickly
- Inspect event history to understand the exact sequence of execution
- Use Workflow IDs that are descriptive and searchable

## Exercise

1. Start the dev server and open the Web UI
2. Run the greeting Workflow project
3. Find the Workflow in the Web UI
4. Inspect the event history and identify each event type
5. View the Activity input and output

See [exercise_02_web_ui_observation.py](../exercises/exercise_02_web_ui_observation.py)
