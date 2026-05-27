```mermaid
graph TD
    A[Start] --> B[Input: country]
    B[Input: country] -- {country} --> C[Send email to user]
    C[Send email to user] -- {email_status} --> D[Wait: 1 minute]
    D[Wait: 1 minute] --> E[Output: email status]
    E[Output: email status] --> F[End]
```