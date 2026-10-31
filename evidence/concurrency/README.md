# Evidence: concurrency control

## Claim
Simultaneous requests for the same contended resource must not over-allocate inventory.

## Evidence
The script in scripts/concurrency_demo.py runs 20 concurrent requests against the Inventory service for product prod-1 with an initial stock of 10.

Expected result:
- exactly 10 requests succeed
- the remaining 10 are rejected with HTTP 409 and an "Insufficient stock" message

## Why this proves the claim
The Inventory service performs the check and update in a single transaction. A plain application-level check-then-update would be vulnerable to race conditions.
