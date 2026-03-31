# Temporal CLI

## Overview

The Temporal CLI (`temporal`) is a command-line tool for interacting with a Temporal Cluster. It can start a development server, manage Workflows, and inspect execution history.

## Installation

```bash
# macOS
brew install temporal

# Linux (via curl)
curl -sSf https://temporal.download/cli.sh | sh

# Verify installation
temporal --version
```

## Starting a Development Server

```bash
temporal server start-dev
```

This starts:
- Temporal Server on `localhost:7233`
- Web UI on `http://localhost:8233`

### With Custom Port

```bash
temporal server start-dev --port 7233 --ui-port 8233
```

### With Custom Namespace

```bash
temporal server start-dev --namespace my-namespace
```

## Workflow Commands

### List Workflows

```bash
temporal workflow list
```

### Start a Workflow

```bash
temporal workflow start \
  --type GreetSomeone \
  --task-queue greeting-tasks \
  --workflow-id my-greeting \
  --input '"Alice"'
```

### Describe a Workflow

```bash
temporal workflow describe --workflow-id my-greeting
```

### Show Workflow History

```bash
temporal workflow show --workflow-id my-greeting
```

### Terminate a Workflow

```bash
temporal workflow terminate --workflow-id my-greeting
```

### Cancel a Workflow

```bash
temporal workflow cancel --workflow-id my-greeting
```

## Common CLI Patterns

### Start Workflow and Wait for Result

```bash
temporal workflow execute \
  --type GreetSomeone \
  --task-queue greeting-tasks \
  --workflow-id my-greeting \
  --input '"Alice"'
```

### View Event History as JSON

```bash
temporal workflow show --workflow-id my-greeting --output json
```

## Python SDK Equivalent

Most CLI operations have Python SDK equivalents:

```python
from temporalio.client import Client

client = await Client.connect("localhost:7233")

# Start workflow
handle = await client.start_workflow(
    GreetSomeone.run,
    "Alice",
    id="my-greeting",
    task_queue="greeting-tasks",
)

# Get result
result = await handle.result()

# Describe workflow
desc = await handle.describe()
```

## Best Practices

- Use the CLI for quick testing and debugging
- Use the Python SDK for production starters
- Use `temporal workflow show` to inspect event history during debugging
- Use `temporal server start-dev` for local development

## Exercise

1. Start the dev server: `temporal server start-dev`
2. List Workflows: `temporal workflow list`
3. Start a Workflow via CLI: `temporal workflow start --type GreetSomeone --task-queue greeting-tasks --input '"World"'`
4. Check the result: `temporal workflow show --workflow-id <id>`
