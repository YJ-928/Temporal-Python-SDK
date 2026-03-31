# Temporal Integration with Applications

## Overview

Temporal integrates into existing applications through **client starters** and **Workers**. Any application can start a Workflow by creating a Temporal client and sending a start request.

## Starting Workflows from Applications

### Basic Starter

```python
import asyncio
from temporalio.client import Client
from workflow import GreetSomeone


async def main():
    client = await Client.connect("localhost:7233")

    handle = await client.start_workflow(
        GreetSomeone.run,
        "Alice",
        id="greeting-workflow",
        task_queue="greeting-tasks",
    )

    print(f"Started workflow. ID: {handle.id}, RunID: {handle.result_run_id}")
    result = await handle.result()
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Start and Fire-and-Forget

```python
handle = await client.start_workflow(
    GreetSomeone.run,
    "Alice",
    id="greeting-workflow",
    task_queue="greeting-tasks",
)
# Don't wait for result — Workflow runs in the background
print(f"Workflow started: {handle.id}")
```

### Execute and Wait

```python
result = await client.execute_workflow(
    GreetSomeone.run,
    "Alice",
    id="greeting-workflow",
    task_queue="greeting-tasks",
)
print(f"Result: {result}")
```

## Workflow IDs

Every Workflow execution needs a unique ID:

```python
handle = await client.start_workflow(
    PizzaOrderWorkflow.order_pizza,
    order,
    id=f"pizza-workflow-order-{order.order_number}",  # Unique ID
    task_queue="pizza-tasks",
)
```

### Best Practices for Workflow IDs

- Use **business-meaningful** IDs: `order-12345`, `user-signup-abc`
- Include a prefix for searchability: `pizza-workflow-order-XD001`
- Temporal rejects duplicate IDs (by default) — this prevents duplicate processing

## Integration with Microservices

Temporal Workflows can call external microservices via Activities:

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/get-spanish-greeting', methods=['GET'])
def spanish_greeting_handler():
    name = request.args.get('name', None)
    if name:
        return f"¡Hola, {name}!", 200
    else:
        return "Missing required 'name' parameter.", 400
```

The Activity calls this microservice:

```python
@activity.defn
async def greet_in_spanish(self, name: str) -> str:
    url = f"http://localhost:9999/get-spanish-greeting?name={urllib.parse.quote(name)}"
    async with self.session.get(url) as response:
        response.raise_for_status()
        return await response.text()
```

## Using Command-Line Arguments

```python
import sys

async def main():
    client = await Client.connect("localhost:7233")

    handle = await client.start_workflow(
        GreetSomeone.run,
        sys.argv[1],                    # Name from CLI
        id="greeting-workflow",
        task_queue="greeting-tasks",
    )
    result = await handle.result()
    print(f"Result: {result}")
```

```bash
python starter.py Alice
```

## Using Dataclasses for Complex Input

```python
from shared import TranslationWorkflowInput

handle = await client.start_workflow(
    TranslationWorkflow.run,
    TranslationWorkflowInput(name=sys.argv[1], language_code=sys.argv[2]),
    id="translation-tasks-example",
    task_queue="translation-tasks",
)
```

```bash
python starter.py Pierre fr
```

## Best Practices

- Use `start_workflow` for fire-and-forget; `execute_workflow` when you need the result
- Use business-meaningful Workflow IDs
- Pass structured data using dataclasses
- Handle `WorkflowFailureError` when waiting for results
- Reuse client connections across multiple Workflow starts

## Exercise

Create a Workflow starter that:
1. Accepts a name from the command line
2. Starts a certificate-generation Workflow
3. Prints the Workflow ID and result

See [exercise_04_finale_workflow.py](../exercises/exercise_04_finale_workflow.py)
