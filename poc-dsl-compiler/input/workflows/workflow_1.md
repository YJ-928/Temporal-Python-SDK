```mermaid
graph TD
    A[Start] --> B[Input: email]
    B[Input: email] -- {user_email} --> C[Geocode location to coordinates]
    C[Geocode location to coordinates] -- {coordinates} --> D[Output: coordinates]
    D[Output: coordinates] --> E[End]
```