from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.subscription_routes import router as subscription_router
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Subscription Service", version="1.0.0", lifespan=lifespan)
app.include_router(subscription_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "subscription-service"}
