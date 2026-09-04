from fastapi import FastAPI

from app.api.sql_routes import router as sql_router

app = FastAPI(title="AI SQL Service", version="1.0.0")
app.include_router(sql_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-sql-service"}
