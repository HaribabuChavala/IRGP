from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth_routes import router as auth_router
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "auth-service"}


app.include_router(auth_router)
