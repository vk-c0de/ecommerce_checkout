import json

import requests

BASE_URL = "http://localhost:8004"

payload = {
    "order_id": "demo-order-1",
    "amount": 119.48,
    "idempotency_key": "same-key-123",
}

first = requests.post(f"{BASE_URL}/api/v1/payments", json=payload, timeout=5)
second = requests.post(f"{BASE_URL}/api/v1/payments", json=payload, timeout=5)
third = requests.post(
    f"{BASE_URL}/api/v1/payments",
    json={
        "order_id": "demo-order-2",
        "amount": 220.0,
        "idempotency_key": "same-key-123",
    },
    timeout=5,
)

print("First call:", first.status_code, first.json())
print("Second call:", second.status_code, second.json())
print("Different payload with same key:", third.status_code, third.json())
print(json.dumps({
    "first": first.json(),
    "second": second.json(),
    "different_payload": third.json(),
}, indent=2))
