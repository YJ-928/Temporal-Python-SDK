# Debugging Workflows

## Overview

Debugging Temporal Workflows involves using the **Temporal Web UI**, **event history**, **logging**, and **tests** to identify and fix issues in Workflow and Activity code.

## Debugging Tools

| Tool | Use Case |
|------|----------|
| Temporal Web UI | Visual inspection of Workflow state and history |
| Event History | Step-by-step execution trace |
| `workflow.logger` | Runtime log messages |
| `activity.logger` | Activity-level logging |
| Tests | Reproduce and verify fixes |
| `temporal workflow show` | CLI-based history inspection |

## Debugging with the Web UI

### Step 1: Find the Workflow

1. Open `http://localhost:8233`
2. Search by Workflow ID or filter by status (Failed, Running, etc.)

### Step 2: Inspect Event History

Look for failure events:

```
ActivityTaskScheduled     ← Activity was dispatched
ActivityTaskStarted       ← Worker picked it up
ActivityTaskFailed        ← Activity raised an exception
  └─ failure: "invalid charge amount: -1500"
```

### Step 3: Examine Activity Input/Output

Each event contains:
- **Input**: The arguments passed to the Activity
- **Output**: The return value (or error)
- **Timestamps**: When each event occurred

## Debugging with Event History CLI

```bash
temporal workflow show --workflow-id pizza-workflow-order-XD001
```

Output:
```
  1  WorkflowExecutionStarted
  2  WorkflowTaskScheduled
  3  WorkflowTaskStarted
  4  WorkflowTaskCompleted
  5  ActivityTaskScheduled     {ActivityType: get_distance}
  6  ActivityTaskStarted
  7  ActivityTaskCompleted     {Result: {kilometers: 20}}
  8  TimerStarted             {Duration: 3s}
  9  TimerFired
 10  ActivityTaskScheduled     {ActivityType: send_bill}
 11  ActivityTaskStarted
 12  ActivityTaskCompleted     {Result: {order_number: XD001, status: SUCCESS}}
 13  WorkflowExecutionCompleted
```

## Common Debugging Scenarios

### 1. Activity Failure — Business Logic Error

**Symptom**: `ActivityTaskFailed` in event history

**Example**: The pizza order Activity fails because the charge amount is negative.

```python
@activity.defn
async def send_bill(self, bill: Bill) -> OrderConfirmation:
    charge_amount = bill.amount

    if charge_amount > 3000:
        charge_amount -= 500

    if charge_amount < 0:
        raise ApplicationError(f"invalid charge amount: {charge_amount}")
```

**Fix**: Validate input before processing.

### 2. Workflow Failure — Service Area Check

**Symptom**: `WorkflowExecutionFailed` with `ApplicationError`

```python
if order.is_delivery and distance.kilometers > 25:
    raise ApplicationError("customer lives outside the service area")
```

**Debug**: Check the `get_distance` Activity result in the event history.

### 3. Non-Determinism Error

**Symptom**: `WorkflowTaskFailed` with non-determinism error

**Cause**: Workflow code changed between replay and original execution.

**Fix**: Don't modify the logic of running Workflows. Use versioning for changes.

### 4. Activity Timeout

**Symptom**: `ActivityTaskTimedOut` in event history

**Fix**: Increase `start_to_close_timeout` or fix the slow Activity.

## Debugging with Tests

Write a test that reproduces the bug:

```python
@pytest.mark.asyncio
async def test_send_bill_fails_negative_amount():
    bill = Bill(
        customer_id=21974,
        order_number="QU812",
        description="1 large supreme pizza",
        amount=-1000,
    )
    with pytest.raises(Exception) as e:
        activity_environment = ActivityEnvironment()
        activities = PizzaOrderActivities()
        await activity_environment.run(activities.send_bill, bill)
    assert "invalid charge amount" in str(e)
```

## Debugging Checklist

1. Check Workflow status in the Web UI
2. Examine the event history for failed events
3. Read the error message and stack trace
4. Check Activity inputs — were they correct?
5. Check Activity code — is the logic right?
6. Write a test to reproduce the bug
7. Fix and verify with the test

## Best Practices

- Use meaningful Workflow IDs to find Workflows easily
- Add `workflow.logger` and `activity.logger` messages at key points
- Write tests for known failure cases
- Use the Web UI event history as the primary debugging tool
- Check for non-determinism issues when Workflows fail during replay

## Exercise

Debug a pizza order Workflow that fails due to incorrect charge calculation:
1. Run the Workflow and observe the failure
2. Inspect the event history in the Web UI
3. Identify the bug in the Activity code
4. Fix the bug and verify with a test

See [exercise_07_debug_activity.py](../exercises/exercise_07_debug_activity.py)
