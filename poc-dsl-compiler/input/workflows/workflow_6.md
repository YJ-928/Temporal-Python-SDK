```mermaid
graph TD
    A[Start] --> B[Input: order id]
    B[Input: order id] -- {order_id} --> C[Fetch product details]
    C[Fetch product details] -- {product_details} --> D[Wait: 5 minutes]
    D[Wait: 5 minutes] --> E[Output: product details]
    E[Output: product details] --> F[End]
```