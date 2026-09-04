from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.users_routes import router as users_router
from app.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="User Management Service", version="1.0.0", lifespan=lifespan)
app.include_router(users_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "user-management-service"}
