```mermaid
graph TD
    A[Start] --> B[Input: name]
    B[Input: name] -- {user_name} --> C[Generate user activity report]
    C[Generate user activity report] -- {report} --> D[Wait: 5 minutes]
    D[Wait: 5 minutes] --> E[Output: report]
    E[Output: report] --> F[End]
```