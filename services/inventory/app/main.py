import os
import sqlite3
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DB_PATH = os.getenv("DATABASE_PATH", "/tmp/inventory.db")
app = FastAPI(title="Inventory Service", version="1.0.0")


class ReserveRequest(BaseModel):
    product_id: str
    quantity: int
    order_id: str


class ReleaseRequest(BaseModel):
    product_id: str
    quantity: int
    order_id: str


class AdjustRequest(BaseModel):
    product_id: str
    quantity: int


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                product_id TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL,
                version INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO inventory(product_id, quantity, version) VALUES(?, ?, 0)",
                [
                    ("prod-1", 10),
                    ("prod-2", 5),
                    ("prod-3", 8),
                    ("prod-4", 12),
                ],
            )
        conn.commit()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "inventory"}


@app.get("/api/v1/inventory")
def list_inventory() -> list:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM inventory ORDER BY product_id").fetchall()
        return [dict(row) for row in rows]


@app.post("/api/v1/inventory/reserve")
def reserve_stock(payload: ReserveRequest) -> dict:
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT quantity, version FROM inventory WHERE product_id = ?",
            (payload.product_id,),
        ).fetchone()
        if row is None:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Product not found in inventory")
        if row[0] < payload.quantity:
            conn.rollback()
            raise HTTPException(status_code=409, detail="Insufficient stock")

        new_quantity = row[0] - payload.quantity
        conn.execute(
            "UPDATE inventory SET quantity = ?, version = version + 1 WHERE product_id = ?",
            (new_quantity, payload.product_id),
        )
        reservation_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO reservations(reservation_id, order_id, product_id, quantity, status) VALUES(?, ?, ?, ?, 'reserved')",
            (reservation_id, payload.order_id, payload.product_id, payload.quantity),
        )
        conn.commit()

    return {
        "reservation_id": reservation_id,
        "product_id": payload.product_id,
        "quantity": payload.quantity,
        "remaining_quantity": new_quantity,
        "status": "reserved",
    }


@app.post("/api/v1/inventory/release")
def release_stock(payload: ReleaseRequest) -> dict:
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE product_id = ?",
            (payload.product_id,),
        ).fetchone()
        if row is None:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Product not found in inventory")
        new_quantity = row[0] + payload.quantity
        conn.execute(
            "UPDATE inventory SET quantity = ?, version = version + 1 WHERE product_id = ?",
            (new_quantity, payload.product_id),
        )
        conn.execute(
            "INSERT INTO reservations(reservation_id, order_id, product_id, quantity, status) VALUES(?, ?, ?, ?, 'released')",
            (uuid.uuid4().hex, payload.order_id, payload.product_id, payload.quantity),
        )
        conn.commit()

    return {
        "product_id": payload.product_id,
        "quantity": payload.quantity,
        "new_quantity": new_quantity,
        "status": "released",
    }


@app.post("/api/v1/inventory/adjust")
def adjust_inventory(payload: AdjustRequest) -> dict:
    if payload.quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE product_id = ?",
            (payload.product_id,),
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO inventory(product_id, quantity, version) VALUES(?, ?, 0)",
                (payload.product_id, payload.quantity),
            )
            conn.commit()
            return {"product_id": payload.product_id, "quantity": payload.quantity, "status": "set"}
        conn.execute(
            "UPDATE inventory SET quantity = ?, version = version + 1 WHERE product_id = ?",
            (payload.quantity, payload.product_id),
        )
        conn.commit()
    return {"product_id": payload.product_id, "quantity": payload.quantity, "status": "updated"}
