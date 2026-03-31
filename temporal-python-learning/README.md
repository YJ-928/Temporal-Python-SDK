# Temporal Python Learning

A comprehensive learning repository for **Temporal 101** and **Temporal 102** courses using the Temporal Python SDK.

---

## Repository Structure

```
temporal-python-learning/
├── README.md
├── requirements.txt
├── .env.example
├── docs/                          # 20 concept documentation files
│   ├── 01_temporal_overview.md
│   ├── 02_temporal_architecture.md
│   ├── ...
│   └── 20_temporal_best_practices.md
├── notebooks/                     # 6 interactive Jupyter notebooks
│   ├── 01_temporal_intro.ipynb
│   ├── ...
│   └── 06_debugging_with_event_history.ipynb
├── exercises/                     # 7 standalone exercises
│   ├── exercise_01_hello_workflow.py
│   ├── ...
│   └── exercise_07_debug_activity.py
├── projects/                      # 3 runnable projects
│   ├── greeting_workflow_project/
│   ├── translation_workflow_project/
│   └── pizza_order_debug_project/
└── utils/                         # Shared utilities
    ├── temporal_client.py
    ├── workflow_helpers.py
    └── activity_helpers.py
```

---

## Prerequisites

- Python 3.10+
- [Temporal CLI](https://docs.temporal.io/cli) installed and running
- A running Temporal dev server

### Start Temporal Dev Server

```bash
temporal server start-dev
```

This starts a Temporal server on `localhost:7233` and the Web UI at `http://localhost:8233`.

---

## Setup

```bash
# Clone the repository
cd temporal-python-learning

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Learning Path

### Temporal 101 — Foundations

| # | Topic | Docs | Exercise |
|---|-------|------|----------|
| 1 | Temporal Overview | [docs/01](docs/01_temporal_overview.md) | — |
| 2 | Architecture | [docs/02](docs/02_temporal_architecture.md) | — |
| 3 | Workflows | [docs/03](docs/03_workflows.md) | [exercise_01](exercises/exercise_01_hello_workflow.py) |
| 4 | Activities | [docs/04](docs/04_activities.md) | [exercise_03](exercises/exercise_03_farewell_workflow.py) |
| 5 | Workers | [docs/05](docs/05_workers.md) | — |
| 6 | Task Queues | [docs/06](docs/06_task_queues.md) | — |
| 7 | Temporal CLI | [docs/07](docs/07_temporal_cli.md) | — |
| 8 | Temporal Web UI | [docs/08](docs/08_temporal_web_ui.md) | [exercise_02](exercises/exercise_02_web_ui_observation.py) |
| 9 | Retry Policies | [docs/09](docs/09_activity_retry_policy.md) | — |
| 10 | Async vs Sync | [docs/10](docs/10_async_vs_sync_activities.md) | — |
| 11 | Deployment | [docs/11](docs/11_temporal_deployment.md) | — |
| 12 | Integration | [docs/12](docs/12_temporal_integration_with_apps.md) | [exercise_04](exercises/exercise_04_finale_workflow.py) |

### Temporal 102 — Durable Execution, Testing, Debugging

| # | Topic | Docs | Exercise |
|---|-------|------|----------|
| 13 | Durable Execution | [docs/13](docs/13_durable_execution.md) | [exercise_05](exercises/exercise_05_durable_execution.py) |
| 14 | Logging | [docs/14](docs/14_temporal_logging.md) | — |
| 15 | Workflow Timers | [docs/15](docs/15_workflow_timers.md) | — |
| 16 | Testing | [docs/16](docs/16_temporal_testing.md) | [exercise_06](exercises/exercise_06_testing_workflow.py) |
| 17 | Time Skipping | [docs/17](docs/17_time_skipping.md) | — |
| 18 | Mocking Activities | [docs/18](docs/18_mocking_activities.md) | — |
| 19 | Debugging | [docs/19](docs/19_debugging_workflows.md) | [exercise_07](exercises/exercise_07_debug_activity.py) |
| 20 | Best Practices | [docs/20](docs/20_temporal_best_practices.md) | — |

### Projects

| Project | Description |
|---------|-------------|
| [Greeting Workflow](projects/greeting_workflow_project/) | Hello world — Activity returns a greeting message |
| [Translation Workflow](projects/translation_workflow_project/) | Durable timers, logging, multi-activity orchestration |
| [Pizza Order Debug](projects/pizza_order_debug_project/) | Activity failure simulation, retry logic, pytest tests |

### Notebooks

| Notebook | Topic |
|----------|-------|
| [01](notebooks/01_temporal_intro.ipynb) | Temporal Introduction |
| [02](notebooks/02_workflows_and_activities.ipynb) | Workflows & Activities |
| [03](notebooks/03_retry_policies.ipynb) | Retry Policies |
| [04](notebooks/04_durable_execution.ipynb) | Durable Execution |
| [05](notebooks/05_testing_workflows.ipynb) | Testing Workflows |
| [06](notebooks/06_debugging_with_event_history.ipynb) | Debugging with Event History |

---

## Running Projects

Each project has four components: workflow, activity, worker, and starter.

```bash
# Terminal 1 — Start Temporal
temporal server start-dev

# Terminal 2 — Start Worker
cd projects/greeting_workflow_project
python worker.py

# Terminal 3 — Run Workflow
cd projects/greeting_workflow_project
python starter.py
```

---

## Running Tests

```bash
# Run all tests
pytest projects/pizza_order_debug_project/tests/ -v

# Run a specific test
pytest projects/pizza_order_debug_project/tests/test_activities.py -v
```

---

## License

Educational use only. Based on Temporal 101 & 102 course materials.
