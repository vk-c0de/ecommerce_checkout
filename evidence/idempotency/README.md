# Evidence: idempotency

## Claim
Repeating an unsafe request with the same idempotency key must return the same result and must not create duplicate effects.

## Evidence
The script in scripts/idempotency_demo.py sends the same payment request twice with the same key and then a third request with the same key but a different payload.

Expected result:
- first call: HTTP 200
- second call: same payment_id, same amount, same status
- third call: HTTP 409 because payload differs for same key

## Why this proves the claim
The Payment service stores the idempotency key and checks it before inserting a new payment. This prevents duplicate charging.
