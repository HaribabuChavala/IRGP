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
    tables = schema_context.get("tables") or ["report_owner.sales_orders"]
    customer_table = next((table for table in tables if str(table).lower().endswith("customers")), tables[0])
    sales_table = next((table for table in tables if str(table).lower().endswith("sales_orders")), tables[-1])

    region_filter = ""
    if any(token in prompt for token in ("only us sales", "us sales", "sales in us", "in us", "usa", "united states")):
        region_filter = " WHERE c.region = 'US' "

    if "count" in prompt and "customer" in prompt:
        sql = f"SELECT COUNT(*) AS customer_count FROM {customer_table}"
    elif "revenue" in prompt or "sales" in prompt:
        sql = (
            f"SELECT c.region AS region, SUM(so.amount) AS total_revenue "
            f"FROM {sales_table} so JOIN {customer_table} c ON c.customer_id = so.customer_id "
            f"{region_filter}"
            "GROUP BY c.region ORDER BY total_revenue DESC FETCH FIRST 100 ROWS ONLY"
        )
    elif "top" in prompt and "product" in prompt:
        sql = (
            f"SELECT product_id, SUM(amount) AS total_revenue FROM {sales_table} "
            "GROUP BY product_id ORDER BY total_revenue DESC FETCH FIRST 100 ROWS ONLY"
        )
    else:
        sql = f"SELECT * FROM {sales_table} FETCH FIRST 100 ROWS ONLY"

    return {
        "sql": sql,
        "dialect": payload.dialect or "oracle",
        "status": "ok",
    }
