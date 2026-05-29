```mermaid
graph TD
    A[Start] --> B[Input: country and order id]
    B[Input: country and order id] -- {country} --> C[Enrich user profile]
    C[Enrich user profile] -- {enriched_profile} --> D[Wait: 1 minute]
    D[Wait: 1 minute] --> E[Look up location data]
    E[Look up location data] -- {location_data} --> F[Output: location data]
    F[Output: location data] --> J[End]
    B[Input: country and order id] -- {order_id} --> G[Process order]
    G[Process order] -- {order_status} --> H[Wait: 5 minutes]
    H[Wait: 5 minutes] --> I[Output: order status]
    I[Output: order status] --> J[End]
```