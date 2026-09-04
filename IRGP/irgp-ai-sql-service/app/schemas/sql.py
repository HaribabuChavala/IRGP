from pydantic import BaseModel, ConfigDict, Field


class DataSourceInfo(BaseModel):
    id: str
    name: str
    type: str
    database: str | None = None


class GenerateSqlRequest(BaseModel):
    prompt: str = Field(min_length=1)
    tenant_id: str
    data_source: DataSourceInfo

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "Show top 10 customers by revenue in current quarter",
                "tenant_id": "tenant-demo",
                "data_source": {
                    "id": "ds-001",
                    "name": "Oracle Sales Mart",
                    "type": "oracle",
                    "database": "testing",
                },
            }
        }
    )


class GenerateSqlResponse(BaseModel):
    sql: str
    dialect: str
    valid: bool
    validation_errors: list[str]
    estimated_cost: str
    pii_detected: bool
    pii_columns: list[str]
    planner_notes: list[str]
    provider: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sql": "SELECT region, SUM(revenue_amount) AS total_revenue FROM testing.sales_orders GROUP BY region ORDER BY total_revenue DESC FETCH FIRST 100 ROWS ONLY",
                "dialect": "oracle",
                "valid": True,
                "validation_errors": [],
                "estimated_cost": "low",
                "pii_detected": False,
                "pii_columns": [],
                "planner_notes": [
                    "Map user intent to business metrics",
                    "Use aggregation on monetary columns",
                    "Group by region for segmented output",
                    "Restrict to allowed tables (4)",
                ],
                "provider": "ai-sql-service-local-fallback",
            }
        }
    )
