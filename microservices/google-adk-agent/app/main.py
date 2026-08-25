from typing import Any
import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Google ADK Agent Mock", version="1.0.0")

EXPECTED_TOKEN = os.getenv("EXPECTED_API_TOKEN", "local-adk-test-key").strip() or "local-adk-test-key"


class AgentRequest(BaseModel):
    task: str = Field(default="generate_sql")
    prompt: str = Field(min_length=1)
    dialect: str = "oracle"
    tenant_id: str | None = None
    data_source: dict[str, Any] | None = None
    schema_context: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "google-adk-agent"}


@app.post("/agent")
async def agent(payload: AgentRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = None
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()

    if token != EXPECTED_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    prompt = payload.prompt.lower()
    schema_context = payload.schema_context or {}
    tables = schema_context.get("tables") or ["testing.sales_orders"]
    table = str(tables[0])

    if "count" in prompt and "customer" in prompt:
        sql = f"SELECT COUNT(*) AS customer_count FROM {table}"
    elif "revenue" in prompt or "sales" in prompt:
        sql = (
            f"SELECT region, SUM(revenue_amount) AS total_revenue FROM {table} "
            "GROUP BY region ORDER BY total_revenue DESC FETCH FIRST 100 ROWS ONLY"
        )
    elif "top" in prompt and "product" in prompt:
        sql = (
            f"SELECT product_id, SUM(revenue_amount) AS total_revenue FROM {table} "
            "GROUP BY product_id ORDER BY total_revenue DESC FETCH FIRST 100 ROWS ONLY"
        )
    else:
        sql = f"SELECT * FROM {table} FETCH FIRST 100 ROWS ONLY"

    return {
        "sql": sql,
        "dialect": payload.dialect or "oracle",
        "status": "ok",
    }
