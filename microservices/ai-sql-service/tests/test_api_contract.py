from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def _apply_strict_defaults() -> None:
    settings.google_adk_agent_url = ""
    settings.google_adk_agent_api_key = ""
    settings.max_sql_limit = 100
    settings.deny_star_select = True
    settings.enforce_row_limit = True
    settings.require_tenant_allowlist = True
    settings.tenant_table_allowlist = {
        "tenant-a": ["testing.sales_orders", "testing.sales_order_items", "testing.customers", "testing.products"],
    }


def test_generate_sql_route_returns_contract() -> None:
    _apply_strict_defaults()

    response = client.post(
        "/generate-sql",
        json={
            "prompt": "Show revenue by region",
            "tenant_id": "tenant-a",
            "data_source": {
                "id": "ds-1",
                "name": "Oracle Sales",
                "type": "oracle",
                "database": "testing",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "sql" in body
    assert "dialect" in body
    assert "valid" in body
    assert "validation_errors" in body
    assert "estimated_cost" in body
    assert "pii_detected" in body
    assert "planner_notes" in body
    assert body["provider"] == "ai-sql-service-local-fallback"


def test_openapi_contains_request_and_response_examples() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200

    document = response.json()
    generate_sql = document["paths"]["/generate-sql"]["post"]

    request_content = generate_sql["requestBody"]["content"]["application/json"]
    request_example = request_content.get("example")
    if request_example is None:
        request_example = request_content.get("examples", {}).get("default", {}).get("value")
    if request_example is None:
        request_example = document["components"]["schemas"]["GenerateSqlRequest"].get("example")

    assert request_example is not None
    assert request_example["prompt"] == "Show top 10 customers by revenue in current quarter"
    assert request_example["tenant_id"] == "tenant-demo"

    response_example = generate_sql["responses"]["200"]["content"]["application/json"]["example"]
    assert "sql" in response_example
    assert "dialect" in response_example
    assert response_example["provider"] in [
        "ai-sql-service-local-fallback",
        "google-adk-remote",
        "google-gemini-api",
    ]
