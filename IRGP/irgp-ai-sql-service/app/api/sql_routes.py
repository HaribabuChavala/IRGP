from fastapi import APIRouter, Body, HTTPException

from app.schemas.sql import GenerateSqlRequest, GenerateSqlResponse
from app.services.pipeline import pipeline

router = APIRouter()


@router.post(
    "/generate-sql",
    response_model=GenerateSqlResponse,
    summary="Generate SQL from natural language",
    responses={
        200: {
            "description": "SQL generation result",
            "content": {
                "application/json": {
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
            },
        }
    },
)
async def generate_sql(
    request: GenerateSqlRequest = Body(
        ...,
        examples={
            "default": {
                "summary": "Revenue query",
                "value": {
                    "prompt": "Show top 10 customers by revenue in current quarter",
                    "tenant_id": "tenant-demo",
                    "data_source": {
                        "id": "ds-001",
                        "name": "Oracle Sales Mart",
                        "type": "oracle",
                        "database": "testing",
                    },
                },
            },
        },
    )
) -> GenerateSqlResponse:
    try:
        result = await pipeline.generate_sql(
            prompt=request.prompt,
            data_source=request.data_source.model_dump(),
            tenant_id=request.tenant_id,
        )
        return GenerateSqlResponse(
            sql=result.sql,
            dialect=result.dialect,
            valid=result.valid,
            validation_errors=result.validation_errors,
            estimated_cost=result.estimated_cost,
            pii_detected=result.pii_detected,
            pii_columns=result.pii_columns,
            planner_notes=result.planner_notes,
            provider=result.provider,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI SQL generation failed: {exc}") from exc
