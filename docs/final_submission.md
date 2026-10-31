# E-commerce Checkout Microservices Project

## Final Project Report

## 1. Introduction

This project implements a microservices-based e-commerce checkout system designed to demonstrate realistic distributed system behavior. Instead of focusing only on CRUD operations, the project addresses the common challenges faced in modern service-oriented systems, including concurrency, duplicate requests, payment safety, and downstream service failure handling.

The system captures a complete checkout workflow that begins when a customer places an order and ends when the payment is approved and a notification is generated. The design is intentionally structured to reflect real-world trade-offs in service ownership, failure isolation, and data consistency.

## 2. Problem Statement and Scope

The objective of this project is to build a working multi-service application that models an online retail checkout flow. The solution must demonstrate the following:

- multiple independent services,
- service-to-service communication over HTTP,
- database-per-service design,
- inventory control under concurrency,
- payment idempotency,
- orchestration of a business transaction across services,
- Docker-based deployment readiness,
- Kubernetes deployment readiness.

The core business flow is as follows:

1. A customer requests an order.
2. The catalog service provides product information and pricing.
3. The inventory service reserves stock.
4. The payment service processes payment using an idempotency key.
5. The order service marks the order as successful.
6. The notification service records the confirmation.

## 3. Business Rules

The application is built around several important business rules:

- BR1: Inventory cannot be over-allocated.
- BR2: A product cannot be reserved if stock is not sufficient.
- BR3: The same payment request with the same idempotency key must return the same result.
- BR4: A payment request with the same key but a different payload must be rejected.
- BR5: An order is confirmed only after payment is successful.
- BR6: If payment fails, the previously reserved stock must be released.

These rules are enforced in the application logic and were validated through live execution.

## 4. System Architecture

The system follows a microservices architecture where each service owns its own data and communicates through REST APIs. This avoids tight coupling and reflects how production systems often separate responsibilities by business domain.

### 4.1 Service decomposition

#### Catalog Service
This service owns product data such as product ID, name, description, and price. It provides product lookup endpoints for the order service.

#### Inventory Service
This service owns stock levels and reservations. It is responsible for checking availability and protecting the stock quantity from race conditions during concurrent reservations.

#### Order Service
This is the orchestration layer of the application. It coordinates the checkout process and calls the other services in the correct sequence.

#### Payment Service
This service owns payment records and idempotency metadata. It prevents accidental duplicate charges by tracking the unique idempotency keys associated with each request.

#### Notification Service
This service stores or records notifications after a successful order payment and confirmation.

## 5. Data Ownership and Database-per-Service

Each service maintains a separate SQLite database to ensure independent ownership of business data. The design is as follows:

- Catalog DB: product catalog and prices
- Inventory DB: stock levels and reservation records
- Order DB: customer orders and items
- Payment DB: payment attempts and idempotency keys
- Notification DB: notification records

No service reads another service's database directly. Instead, services exchange only the required identifiers and payloads through HTTP APIs. This keeps the architecture aligned with the database-per-service pattern.

## 6. API Design

The project exposes versioned REST endpoints for each service.

### Catalog endpoints
- GET /health
- GET /api/v1/products
- GET /api/v1/products/{product_id}

### Inventory endpoints
- GET /health
- GET /api/v1/inventory
- POST /api/v1/inventory/reserve
- POST /api/v1/inventory/release
- POST /api/v1/inventory/adjust

### Order endpoints
- GET /health
- POST /api/v1/orders
- GET /api/v1/orders/{order_id}

### Payment endpoints
- GET /health
- POST /api/v1/payments
- GET /api/v1/payments/{payment_id}

### Notification endpoints
- GET /health
- POST /api/v1/notifications

## 7. Key Technical Challenges and Their Solutions

### 7.1 Concurrency and inventory safety

One of the main challenges in this project is protecting inventory during concurrent order attempts. If two or more requests try to reserve the same product simultaneously, the system can easily allow over-allocation if the stock check and update are not atomic.

The solution is implemented in the inventory service by validating and updating stock in a single transactional operation. This ensures that only a valid number of reservations succeed, while the others fail with a conflict response.

### 7.2 Payment idempotency

The payment flow is the second major challenge. In real-world systems, repeated requests from client retries or network timeouts can cause the same payment to be processed more than once. This is dangerous because it can result in duplicate charges.

The payment service solves this by storing a unique idempotency key for each payment request. If the same key is repeated with the same payload, the system returns the same result. If the same key is used with a different payload, the request is rejected.

### 7.3 Failure handling and resilience

The project also models realistic failure behavior. The payment service can simulate delayed or failed downstream processing. The order workflow responds appropriately without creating duplicate effects or inconsistent stock states. This makes the application a better demonstration of real distributed-system principles than a simple sample app.

## 8. Deployment and Runtime Execution

The application is containerized and can be launched with Docker Compose.

```bash
cd /home/vijay/Desktop/bits/ecommerce_checkout
docker compose up --build
```

Each service exposes a health endpoint for operational validation. The project also includes Kubernetes manifests under the k8s directory for deployment readiness in a cluster environment.

## 9. Verification and Evidence

The implementation was verified by running the actual services and executing challenge scripts on the local Ubuntu machine.

### 9.1 Concurrency evidence

The concurrency demo was executed against a product with stock of 10. Twenty simultaneous reservation requests were sent to the system. The observed result was:

- 10 successful reservations
- 10 rejected requests due to insufficient stock

This confirms that the inventory service prevents over-allocation under pressure.

### 9.2 Idempotency evidence

The payment idempotency script was executed with the same idempotency key repeated multiple times. The result showed:

- repeated request with same key returned the same successful payment state,
- request with same key but different payload was rejected with an HTTP 409 conflict.

This demonstrates that duplicate payment requests are handled safely.

### 9.3 End-to-end order flow

A full order request was also executed successfully through the order service. The response showed that the order was created and the notification was processed successfully along with payment confirmation. This validates the multi-service transaction flow end-to-end.

## 10. Why This Project Is a Good Microservices Demonstration

This project demonstrates several important principles of microservices design:

- clear service boundaries,
- independent data ownership,
- HTTP-based service calls,
- operational visibility through health checks,
- transaction orchestration across services,
- protection from concurrency bugs,
- safe handling of duplicate requests,
- readiness for containerized deployment.

It is a strong example of a distributed system that goes beyond simple application layering and addresses the challenges that real platforms face when business logic spans multiple services.

## 11. Conclusion

The E-commerce Checkout Microservices project successfully demonstrates a realistic and working microservices application with a clear business workflow, distributed responsibilities, and effective protection against key reliability issues. The system handles concurrent inventory requests safely, prevents duplicate payment processing through idempotency keys, and maintains a valid end-to-end order flow while remaining deployable through Docker and Kubernetes.

This project shows that correctness in distributed systems depends not only on service decomposition but also on enforcing business consistency at the right boundaries. The inventory reservation logic and payment idempotency mechanisms are the key technical strengths of the solution.

## 12. AI Usage Declaration

AI tools were used to design the microservice architecture, generate the initial service structure, plan the distributed-system challenge handling, and validate the runtime behavior. The final implementation was then tested on an Ubuntu machine using Docker Compose and live service execution.
