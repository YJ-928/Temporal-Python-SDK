```mermaid
graph TD
    A[Start] --> B[Input: email]
    B[Input: email] -- {user_email} --> C[Look up location data]
    C[Look up location data] -- {location_data} --> D[Output: location data]
    D[Output: location data] --> E[End]
```