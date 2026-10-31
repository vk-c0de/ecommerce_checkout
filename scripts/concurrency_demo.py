import concurrent.futures
import json

import requests

BASE_URL = "http://localhost:8002"


reset_response = requests.post(f"{BASE_URL}/api/v1/inventory/adjust", json={"product_id": "prod-1", "quantity": 10}, timeout=5)
print("Inventory reset:", reset_response.status_code, reset_response.json())


def reserve_once(idx: int):
    payload = {
        "product_id": "prod-1",
        "quantity": 1,
        "order_id": f"concurrency-order-{idx}",
    }
    response = requests.post(f"{BASE_URL}/api/v1/inventory/reserve", json=payload, timeout=5)
    return response.status_code, response.json()


if __name__ == "__main__":
    print("Running inventory concurrency demo against prod-1 with initial stock 10")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(reserve_once, range(20)))

    success_count = sum(1 for status, _ in results if status == 200)
    failure_count = sum(1 for status, _ in results if status != 200)
    print(f"Successful reservations: {success_count}")
    print(f"Rejected reservations: {failure_count}")
    print(json.dumps([{"status": status, "body": body} for status, body in results], indent=2))
