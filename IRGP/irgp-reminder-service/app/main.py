from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.reminder_routes import router as reminder_router
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Reminder Service", version="1.0.0", lifespan=lifespan)
app.include_router(reminder_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "reminder-service"}
