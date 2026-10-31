import os
import random
import sqlite3
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = os.getenv("DATABASE_PATH", "/tmp/payment.db")
app = FastAPI(title="Payment Service", version="1.0.0")


class PaymentRequest(BaseModel):
    order_id: str
    amount: float
    idempotency_key: str


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE
            )
            """
        )
        conn.commit()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "payment"}


@app.get("/api/v1/payments/{payment_id}")
def get_payment(payment_id: str) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM payments WHERE payment_id = ?",
            (payment_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        return dict(row)


@app.post("/api/v1/payments")
def create_payment(payload: PaymentRequest) -> dict:
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        existing = conn.execute(
            "SELECT * FROM payments WHERE idempotency_key = ?",
            (payload.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["order_id"] != payload.order_id or float(existing["amount"]) != float(payload.amount):
                raise HTTPException(status_code=409, detail="Idempotency key reused with different payload")
            return {
                "payment_id": existing["payment_id"],
                "order_id": existing["order_id"],
                "amount": existing["amount"],
                "status": existing["status"],
                "idempotency_key": existing["idempotency_key"],
            }

    failure_rate = float(os.getenv("PAYMENT_FAILURE_RATE", "0"))
    if failure_rate > 0 and random.random() < failure_rate:
        raise HTTPException(status_code=503, detail="Payment gateway simulated failure")

    payment_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO payments(payment_id, order_id, amount, status, idempotency_key) VALUES(?, ?, ?, 'paid', ?)",
        (payment_id, payload.order_id, payload.amount, payload.idempotency_key),
    )
    conn.commit()

    return {
        "payment_id": payment_id,
        "order_id": payload.order_id,
        "amount": payload.amount,
        "status": "paid",
        "idempotency_key": payload.idempotency_key,
    }
