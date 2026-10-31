# Evidence: end-to-end checkout

## Claim
The main application workflow completes successfully across all microservices.

## Evidence
A POST to the Order service triggers product lookup, stock reservation, payment, and notification sending.

Expected result:
- order created successfully,
- status is paid,
- total amount is computed,
- payment_id is returned,
- notification_status is 200.
