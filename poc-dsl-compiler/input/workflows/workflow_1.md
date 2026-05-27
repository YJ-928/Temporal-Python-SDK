```mermaid
graph TD
    A[Start] --> B[Input: phone number]
    B[Input: phone number] -- {phone} --> C[Log user activity]
    C[Log user activity] -- {log_id} --> D[Output: log id]
    D[Output: log id] --> E[End]
```