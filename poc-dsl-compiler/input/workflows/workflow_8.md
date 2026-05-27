```mermaid
graph TD
    A[Start] --> B[Input: order id]
    B[Input: order id] -- {order_id} --> C[Validate email address]
    C[Validate email address] -- {validation_result} --> D[Listen: notification ack]
    D[Listen: notification ack] --> E[Output: validation result]
    E[Output: validation result] --> F[End]
```