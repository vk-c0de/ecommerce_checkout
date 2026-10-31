import os
import sqlite3
import uuid
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

DB_PATH = os.getenv("DATABASE_PATH", "/tmp/notification.db")
app = FastAPI(title="Notification Service", version="1.0.0")


class NotificationRequest(BaseModel):
    order_id: str
    customer_id: str
    message: str


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued'
            )
            """
        )
        conn.commit()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "notification"}


@app.post("/api/v1/notifications")
def create_notification(payload: NotificationRequest) -> dict:
    notification_id = uuid.uuid4().hex
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO notifications(notification_id, order_id, customer_id, message, status) VALUES(?, ?, ?, ?, 'queued')",
            (notification_id, payload.order_id, payload.customer_id, payload.message),
        )
        conn.commit()
    return {
        "notification_id": notification_id,
        "order_id": payload.order_id,
        "customer_id": payload.customer_id,
        "status": "queued",
    }
