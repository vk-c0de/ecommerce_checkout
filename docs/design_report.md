# Design and Technical Report

## 1. Problem and scope

This project implements an e-commerce checkout system using a microservices architecture. The system supports product lookup, stock reservation, order creation, payment processing, and notification dispatch. The design is intentionally small but realistic enough to exercise distributed-system concerns such as concurrency, idempotency, and downstream failure.

### Assumptions
- The system is a single-tenant internal demo application.
- Users place orders with a simple cart of product IDs and quantities.
- Product pricing is managed by the Catalog service.
- Payment is handled by a mock payment gateway implemented inside the Payment service.
- All services are independently deployable and use a separate SQLite database.

### Business rules
- BR1: An item cannot be reserved if inventory is insufficient.
- BR2: An order cannot be paid twice for the same request.
- BR3: Payment and order creation must be idempotent using an idempotency key.
- BR4: An order is confirmed only after payment succeeds.
- BR5: If payment fails, already-reserved inventory must be released.

### Out of scope
- User authentication or authorization
- Real payment gateway integration
- Frontend UI
- Advanced analytics and reporting
- Kafka/RabbitMQ event streaming (not used in this version)

## 2. Service decomposition

### Service responsibilities

Catalog Service
- Owns product catalog and pricing information.
- Provides product lookup for orders.
- Exposes a simple read-only product API.

Inventory Service
- Owns stock count per product.
- Reserves and releases stock.
- Implements concurrency-safe stock updates using a database transaction and conditional checks.

Order Service
- Owns customer orders and order items.
- Orchestrates the business transaction.
- Calls Catalog, Inventory, Payment, and Notification services.

Payment Service
- Owns payments and idempotency records.
- Accepts payment requests with idempotency keys.
- Returns the same result for repeated requests with the same key.

Notification Service
- Owns notification records.
- Queues confirmation messages after successful order completion.

### Why these boundaries are appropriate
The services separate business concerns cleanly and keep data ownership aligned with responsibility. Catalog, inventory, payment, and notification each manage distinct business data, so the system avoids cross-service joins and tightly coupled logic. The Order service is the orchestration layer and is the point where the checkout workflow is coordinated.

### Alternatives rejected
- One monolith service: too coupled and does not satisfy database-per-service requirements.
- Splitting by tables rather than business responsibility: would produce poor boundaries and artificial services.
- Payment logic inside Order service: would violate service ownership design and reduce separation of concerns.

## 3. Architecture

### Component diagram

```text
Client
  |
  v
Order Service ----------------------------+
  |                                      |
  |-- calls Catalog Service               |
  |-- calls Inventory Service             |
  |-- calls Payment Service               |
  |-- calls Notification Service          |
  |                                      |
  +--------------------------------------+

Catalog DB    Inventory DB    Order DB    Payment DB    Notification DB
```

### Main transaction: happy path

```text
Client -> Order Service: POST /api/v1/orders
Order Service -> Catalog Service: GET product details
Catalog Service -> Order Service: product + price
Order Service -> Inventory Service: reserve stock
Inventory Service -> Order Service: reservation success
Order Service -> Payment Service: create payment (Idempotency-Key)
Payment Service -> Order Service: payment success
Order Service -> Notification Service: send confirmation
Notification Service -> Order Service: queued
Order Service -> Client: 200 OK with order + payment details
```

### Failure path

```text
Order Service -> Inventory Service: reserve stock
Inventory Service -> Order Service: insufficient stock
Order Service -> Client: 409 Conflict
```

A second failure path is payment failure:
- inventory reservation is released,
- order is not confirmed,
- user receives a controlled failure response.

## 4. Data design

### Service-level data ownership

Catalog DB
- products
- product name
- price
- description

Inventory DB
- inventory
- reservations
- stock quantity
- version field for concurrency safety

Order DB
- orders
- order_items
- status
- total_amount
- payment_id
- idempotency_key

Payment DB
- payments
- idempotency_key
- amount
- status

Notification DB
- notifications
- order_id
- customer_id
- message
- status

### Cross-service references
Cross-service references are handled using IDs only. For example:
- Order stores product_id values from Catalog and Inventory references.
- Payment stores order_id rather than a full order object.
- Notification stores order_id and customer_id.

This avoids cross-service database joins and keeps each database isolated.

## 5. API design

### Endpoint summary

Catalog Service
- GET /health
- GET /api/v1/products
- GET /api/v1/products/{product_id}

Inventory Service
- GET /health
- GET /api/v1/inventory
- POST /api/v1/inventory/reserve
- POST /api/v1/inventory/release
- POST /api/v1/inventory/adjust

Order Service
- GET /health
- POST /api/v1/orders
- GET /api/v1/orders/{order_id}

Payment Service
- GET /health
- POST /api/v1/payments
- GET /api/v1/payments/{payment_id}

Notification Service
- GET /health
- POST /api/v1/notifications

### Example request

```json
{
  "customer_id": "customer-1",
  "items": [
    { "product_id": "prod-1", "quantity": 1 },
    { "product_id": "prod-2", "quantity": 2 }
  ],
  "idempotency_key": "order-key-001"
}
```

### Example success response

```json
{
  "order_id": "bb3e4c6d...",
  "customer_id": "customer-1",
  "status": "paid",
  "total_amount": 208.99,
  "payment_id": "626966d1...",
  "notification_status": 200,
  "items": [
    { "product_id": "prod-1", "quantity": 1, "unit_price": 29.99 },
    { "product_id": "prod-2", "quantity": 2, "unit_price": 89.5 }
  ]
}
```

## 6. Engineering challenges implemented

### Challenge 1: Concurrency control
The Inventory service checks available stock in a single transaction and rejects requests when stock is insufficient. This prevents over-allocation under parallel requests. In the demo, 20 parallel requests for the same product with stock 10 resulted in exactly 10 accepted requests and 10 rejections.

### Challenge 2: Idempotency
The Payment service stores the idempotency key and maps it to the original response. Repeated requests with the same key result in the same payment result. Requests with the same key but a different payload return HTTP 409.

### Challenge 3: Resilience (selected)
The service design includes a mock payment gateway and supports failing or delayed downstream calls. The order flow is resilient enough to handle partial failures and still return a controlled error without double-processing the request.

## 7. Deployment readiness

The project is designed to run in Docker Compose and can also be mapped to Kubernetes manifests. Service configuration is passed through environment variables, and each service exposes /health for operational checks.

## 8. Appendix A: Contribution and reflection

Single-author version:
- Built the full microservice design and runnable project.
- Solved the stock-concurrency challenge by making inventory reservation atomic and transaction-based.
- Solved idempotency by storing payment keys and rejecting mismatched payloads.
- The hardest problem was coordinating async downstream calls without causing duplicate effects.
- If I had more time, I would add explicit retry/backoff policy and structured correlation IDs to every request.

## 9. Appendix B: AI use declaration

This project used AI assistance to:
- structure the microservice design,
- draft a realistic e-commerce checkout architecture,
- generate the service skeleton and implementation plan,
- validate the application flow and evidence collection.

The final implementation and verification were checked against live Docker execution in the local Ubuntu environment.
