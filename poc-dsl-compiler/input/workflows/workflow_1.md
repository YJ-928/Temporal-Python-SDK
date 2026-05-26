```mermaid
graph TD
    A[Start] --> B[Input: location]
    B[Input: location] -- {user_location} --> C[Enrich user profile]
    C[Enrich user profile] -- {enriched_profile} --> D[Output: enriched profile]
    D[Output: enriched profile] --> E[End]
```