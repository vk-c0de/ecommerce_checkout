import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException

DB_PATH = os.getenv("DATABASE_PATH", "/tmp/catalog.db")
app = FastAPI(title="Catalog Service", version="1.0.0")


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                description TEXT
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO products(product_id, name, price, description) VALUES(?, ?, ?, ?)",
                [
                    ("prod-1", "Wireless Mouse", 29.99, "Ergonomic USB mouse"),
                    ("prod-2", "Mechanical Keyboard", 89.5, "Compact RGB keyboard"),
                    ("prod-3", "4K Monitor", 349.0, "27-inch display"),
                    ("prod-4", "USB-C Hub", 49.99, "7-in-1 connectivity hub"),
                ],
            )
        conn.commit()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "catalog"}


@app.get("/api/v1/products")
def list_products() -> list:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM products ORDER BY product_id").fetchall()
        return [dict(row) for row in rows]


@app.get("/api/v1/products/{product_id}")
def get_product(product_id: str) -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM products WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return dict(row)
