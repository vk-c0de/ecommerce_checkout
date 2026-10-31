import os
import sqlite3
import uuid
from pathlib import Path

import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

DB_PATH = os.getenv("DATABASE_PATH", "/tmp/order.db")
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://localhost:8001")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8002")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8004")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8005")

app = FastAPI(title="Order Service", version="1.0.0")


class OrderItem(BaseModel):
    product_id: str
    quantity: int


class CreateOrderRequest(BaseModel):
    customer_id: str
    items: list[OrderItem]
    idempotency_key: str | None = None


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                total_amount REAL NOT NULL,
                payment_id TEXT,
                idempotency_key TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                order_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL
            )
            """
        )
        conn.commit()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "order"}


@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: str) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        order_row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if order_row is None:
            raise HTTPException(status_code=404, detail="Order not found")
        items = conn.execute(
            "SELECT * FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        row = dict(order_row)
        row["items"] = [dict(item) for item in items]
        return row


def release_inventory_for_order(items: list[OrderItem], headers: dict) -> None:
    for item in items:
        response = requests.post(
            f"{INVENTORY_SERVICE_URL}/api/v1/inventory/release",
            json={"product_id": item.product_id, "quantity": item.quantity, "order_id": "release"},
            headers=headers,
            timeout=5,
        )
        if response.status_code >= 400:
            continue


@app.post("/api/v1/orders")
def create_order(payload: CreateOrderRequest, x_correlation_id: str | None = Header(default=None, alias="X-Correlation-ID")) -> dict:
    headers = {"Content-Type": "application/json"}
    if x_correlation_id:
        headers["X-Correlation-ID"] = x_correlation_id

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if payload.idempotency_key:
            existing = conn.execute(
                "SELECT * FROM orders WHERE idempotency_key = ?",
                (payload.idempotency_key,),
            ).fetchone()
            if existing is not None:
                return dict(existing)

    if not payload.items:
        raise HTTPException(status_code=400, detail="At least one item is required")

    order_id = uuid.uuid4().hex
    total_amount = 0.0
    item_rows = []
    reserved = []

    try:
        for item in payload.items:
            product_response = requests.get(
                f"{CATALOG_SERVICE_URL}/api/v1/products/{item.product_id}",
                headers=headers,
                timeout=5,
            )
            if product_response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            product = product_response.json()
            total_amount += float(product["price"]) * int(item.quantity)
            item_rows.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": float(product["price"]),
                "total_price": float(product["price"]) * int(item.quantity),
            })

        for item in payload.items:
            reserve_response = requests.post(
                f"{INVENTORY_SERVICE_URL}/api/v1/inventory/reserve",
                json={"product_id": item.product_id, "quantity": item.quantity, "order_id": order_id},
                headers=headers,
                timeout=5,
            )
            if reserve_response.status_code != 200:
                raise HTTPException(status_code=409, detail=f"Inventory reserve failed for {item.product_id}")
            reserved.append(item)

        payment_response = requests.post(
            f"{PAYMENT_SERVICE_URL}/api/v1/payments",
            json={
                "order_id": order_id,
                "amount": total_amount,
                "idempotency_key": payload.idempotency_key or f"order-{order_id}",
            },
            headers=headers,
            timeout=5,
        )
        if payment_response.status_code != 200:
            for item in reserved:
                requests.post(
                    f"{INVENTORY_SERVICE_URL}/api/v1/inventory/release",
                    json={"product_id": item.product_id, "quantity": item.quantity, "order_id": order_id},
                    headers=headers,
                    timeout=5,
                )
            raise HTTPException(status_code=402, detail="Payment failed")
        payment = payment_response.json()

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO orders(order_id, customer_id, status, total_amount, payment_id, idempotency_key) VALUES(?, ?, 'paid', ?, ?, ?)",
                (order_id, payload.customer_id, total_amount, payment["payment_id"], payload.idempotency_key or f"order-{order_id}"),
            )
            conn.executemany(
                "INSERT INTO order_items(order_id, product_id, quantity, unit_price, total_price) VALUES(?, ?, ?, ?, ?)",
                [
                    (order_id, row["product_id"], row["quantity"], row["unit_price"], row["total_price"])
                    for row in item_rows
                ],
            )
            conn.commit()

        notification_response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/api/v1/notifications",
            json={
                "order_id": order_id,
                "customer_id": payload.customer_id,
                "message": f"Order {order_id} confirmed successfully",
            },
            headers=headers,
            timeout=5,
        )

        return {
            "order_id": order_id,
            "customer_id": payload.customer_id,
            "status": "paid",
            "total_amount": total_amount,
            "payment_id": payment["payment_id"],
            "notification_status": notification_response.status_code,
            "items": item_rows,
        }
    except HTTPException:
        raise
    except Exception as exc:
        for item in reserved:
            requests.post(
                f"{INVENTORY_SERVICE_URL}/api/v1/inventory/release",
                json={"product_id": item.product_id, "quantity": item.quantity, "order_id": order_id},
                headers=headers,
                timeout=5,
            )
        raise HTTPException(status_code=500, detail=str(exc))
