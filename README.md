# E-commerce Checkout Microservices Demo

This is a runnable microservices demo implementing an e-commerce checkout flow with five services:

- Catalog Service
- Inventory Service
- Order Service
- Payment Service
- Notification Service

It is designed for the WILP Scalable Services assignment and demonstrates:

- database-per-service
- REST over HTTP
- health endpoints
- structured logging and request IDs
- idempotency for payment requests
- concurrency control on stock reserves
- Docker Compose deployment
- Kubernetes deployment manifests

## Run locally with Docker Compose

```bash
cd ecommerce_checkout
docker compose up --build
```

Then test:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

Create an order:

```bash
curl -X POST http://localhost:8003/api/v1/orders \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": "customer-1",
    "items": [
      {"product_id": "prod-1", "quantity": 1},
      {"product_id": "prod-2", "quantity": 2}
    ],
    "idempotency_key": "order-key-001"
  }'
```

## Run locally without Docker

Each service can also be started with uvicorn:

```bash
cd ecommerce_checkout/services/catalog
python3 -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001
```

## Evidence and challenge scripts

```bash
cd ecommerce_checkout
python3 scripts/concurrency_demo.py
python3 scripts/idempotency_demo.py
```

## Folder structure

- services/ : all microservices
- k8s/ : Kubernetes manifests
- scripts/ : challenge scripts
- data/ : SQLite databases created at runtime

## Notes

- Each service has its own SQLite database.
- Payment idempotency is enforced using a unique key per request.
- Inventory reserve calls use atomic update logic to prevent over-allocation.
