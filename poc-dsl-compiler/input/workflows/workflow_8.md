```mermaid
graph TD
    A[Start] --> B[Input: order id]
    B[Input: order id] -- {order_id} --> C[Geocode location to coordinates]
    C[Geocode location to coordinates] -- {coordinates} --> D[Listen: user confirmation]
    D[Listen: user confirmation] --> E[Output: coordinates]
    E[Output: coordinates] --> F[End]
```