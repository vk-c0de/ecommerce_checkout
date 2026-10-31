# Demo Script for Viva / Video Presentation

## 1. Start the application

```bash
cd /home/vijay/Desktop/bits/ecommerce_checkout
docker compose up --build
```

## 2. Show service health

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

Expected result: each service responds with status ok.

## 3. Create a normal order

```bash
curl -X POST http://localhost:8003/api/v1/orders \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": "customer-demo",
    "items": [
      {"product_id": "prod-1", "quantity": 1},
      {"product_id": "prod-2", "quantity": 2}
    ],
    "idempotency_key": "demo-order-1"
  }'
```

Expected result: order is paid, total amount computed, notification status is 200.

## 4. Demonstrate concurrency control

```bash
python3 scripts/concurrency_demo.py
```

Explain:
- 20 requests fired at once,
- inventory has only 10 units,
- exactly 10 succeed,
- the rest are rejected.

## 5. Demonstrate idempotency

```bash
python3 scripts/idempotency_demo.py
```

Explain:
- same idempotency key plus same payload returns same result,
- same key plus different payload returns 409,
- duplicate requests do not create a second payment.

## 6. Close the demonstration

Summarize:
- the system is distributed,
- each service owns its data,
- stock is protected under concurrency,
- duplicate payment requests are prevented,
- the deployment works with Docker Compose.
