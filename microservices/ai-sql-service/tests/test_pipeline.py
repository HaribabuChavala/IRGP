import asyncio

from app.config import settings
from app.services.pipeline import SqlAgentPipeline


def _apply_strict_defaults() -> None:
    settings.google_adk_agent_url = ""
    settings.google_adk_agent_api_key = ""
    settings.google_gemini_model = "gemini-3.6-flash"
    settings.max_sql_limit = 100
    settings.deny_star_select = True
    settings.enforce_row_limit = True
    settings.require_tenant_allowlist = True
    settings.tenant_table_allowlist = {
        "tenant-a": ["testing.sales_orders", "testing.sales_order_items", "testing.customers", "testing.products"],
        "tenant-wild": ["testing.*"],
    }


def test_generate_sql_local_valid_for_tenant_allowlist() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()

    result = asyncio.run(
        pipeline.generate_sql(
            prompt="Show revenue by region",
            data_source={"id": "ds-1", "name": "Oracle Sales", "type": "oracle", "database": "testing"},
            tenant_id="tenant-a",
        )
    )

    assert result.valid is True
    assert "SELECT" in result.sql.upper()
    assert result.provider == "ai-sql-service-local-fallback"


def test_deny_star_select() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()
    schema = {"allow_list": {"testing.sales_orders"}}

    valid, errors = pipeline._validate_sql(
        "SELECT * FROM testing.sales_orders LIMIT 10",
        schema,
        "tenant-a",
    )

    assert valid is False
    assert any("Wildcard SELECT" in item for item in errors)


def test_enforce_max_limit() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()
    schema = {"allow_list": {"testing.sales_orders"}}

    valid, errors = pipeline._validate_sql(
        "SELECT region FROM testing.sales_orders LIMIT 500",
        schema,
        "tenant-a",
    )

    assert valid is False
    assert any("exceeds max allowed" in item for item in errors)


def test_require_explicit_tenant_allowlist() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()
    schema = {"allow_list": {"testing.sales_orders"}}

    valid, errors = pipeline._validate_sql(
        "SELECT region FROM testing.sales_orders LIMIT 10",
        schema,
        "tenant-unknown",
    )

    assert valid is False
    assert any("no explicit table allow-list" in item for item in errors)


def test_tenant_wildcard_allowlist_is_supported() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()
    schema = {"allow_list": {"testing.sales_orders"}}

    valid, errors = pipeline._validate_sql(
        "SELECT region FROM testing.sales_orders LIMIT 10",
        schema,
        "tenant-wild",
    )

    assert valid is True
    assert errors == []


def test_extract_sql_from_text_code_block() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()

    text = """Here is the SQL:\n```sql\nSELECT region FROM testing.sales_orders FETCH FIRST 10 ROWS ONLY\n```"""
    sql = pipeline._extract_sql_from_text(text)

    assert sql == "SELECT region FROM testing.sales_orders FETCH FIRST 10 ROWS ONLY"


def test_extract_sql_from_gemini_response() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()

    body = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "SELECT region, SUM(revenue_amount) AS total_revenue FROM testing.sales_orders GROUP BY region"
                        }
                    ]
                }
            }
        ]
    }

    sql = pipeline._extract_sql_from_gemini_response(body)
    assert sql == "SELECT region, SUM(revenue_amount) AS total_revenue FROM testing.sales_orders GROUP BY region"


def test_gemini_wildcard_retry_generates_valid_sql() -> None:
    _apply_strict_defaults()
    settings.google_adk_agent_url = "https://generativelanguage.googleapis.com/v1beta"
    pipeline = SqlAgentPipeline()

    calls: list[str] = []

    async def fake_generate(payload: dict) -> tuple[str, str] | None:
        calls.append(payload["prompt"])
        if len(calls) == 1:
            return "SELECT * FROM testing.sales_orders FETCH FIRST 10 ROWS ONLY", "google-gemini-api"
        return "SELECT region FROM testing.sales_orders FETCH FIRST 10 ROWS ONLY", "google-gemini-api"

    pipeline._generate_via_google_adk = fake_generate  # type: ignore[method-assign]

    result = asyncio.run(
        pipeline.generate_sql(
            prompt="Show revenue by region",
            data_source={"id": "ds-1", "name": "Oracle Sales", "type": "oracle", "database": "testing"},
            tenant_id="tenant-a",
        )
    )

    assert len(calls) == 2
    assert "Never use SELECT *" in calls[1]
    assert result.valid is True
    assert result.provider == "google-gemini-api"
    assert any("Retried generation" in note for note in result.planner_notes)


def test_gemini_no_retry_when_non_wildcard_error() -> None:
    _apply_strict_defaults()
    settings.google_adk_agent_url = "https://generativelanguage.googleapis.com/v1beta"
    pipeline = SqlAgentPipeline()

    calls: list[str] = []

    async def fake_generate(payload: dict) -> tuple[str, str] | None:
        calls.append(payload["prompt"])
        return "SELECT region FROM testing.sales_orders LIMIT 500", "google-gemini-api"

    pipeline._generate_via_google_adk = fake_generate  # type: ignore[method-assign]

    result = asyncio.run(
        pipeline.generate_sql(
            prompt="Show revenue by region",
            data_source={"id": "ds-1", "name": "Oracle Sales", "type": "oracle", "database": "testing"},
            tenant_id="tenant-a",
        )
    )

    assert len(calls) == 1
    assert result.valid is False
    assert any("exceeds max allowed" in item for item in result.validation_errors)


def test_repair_wildcard_sql_expands_columns_with_alias() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()
    schema = {
        "columns": {
            "testing.sales_orders": ["order_id", "customer_id", "order_date", "region", "total_amount"]
        }
    }

    repaired = pipeline._repair_wildcard_sql(
        "SELECT so.* FROM testing.sales_orders so FETCH FIRST 10 ROWS ONLY",
        schema,
    )

    assert repaired is not None
    assert "SELECT so.order_id, so.customer_id, so.order_date, so.region FROM" in repaired


def test_gemini_retry_then_deterministic_repair_makes_valid() -> None:
    _apply_strict_defaults()
    settings.google_adk_agent_url = "https://generativelanguage.googleapis.com/v1beta"
    pipeline = SqlAgentPipeline()

    async def fake_generate(payload: dict) -> tuple[str, str] | None:
        return "SELECT * FROM testing.sales_orders FETCH FIRST 10 ROWS ONLY", "google-gemini-api"

    pipeline._generate_via_google_adk = fake_generate  # type: ignore[method-assign]

    result = asyncio.run(
        pipeline.generate_sql(
            prompt="Show revenue by region",
            data_source={"id": "ds-1", "name": "Oracle Sales", "type": "oracle", "database": "testing"},
            tenant_id="tenant-a",
        )
    )

    assert result.valid is True
    assert "SELECT order_id, customer_id, order_date, region FROM testing.sales_orders" in result.sql
    assert any("Retried generation" in note for note in result.planner_notes)
    assert any("deterministic wildcard repair" in note for note in result.planner_notes)


def test_apply_row_limit_guard_oracle() -> None:
    _apply_strict_defaults()
    pipeline = SqlAgentPipeline()

    guarded = pipeline._apply_row_limit_guard("SELECT region FROM testing.sales_orders", "oracle")

    assert guarded == "SELECT region FROM testing.sales_orders FETCH FIRST 100 ROWS ONLY"


def test_gemini_row_limit_guard_makes_valid() -> None:
    _apply_strict_defaults()
    settings.google_adk_agent_url = "https://generativelanguage.googleapis.com/v1beta"
    pipeline = SqlAgentPipeline()

    async def fake_generate(payload: dict) -> tuple[str, str] | None:
        return "SELECT region FROM testing.sales_orders", "google-gemini-api"

    pipeline._generate_via_google_adk = fake_generate  # type: ignore[method-assign]

    result = asyncio.run(
        pipeline.generate_sql(
            prompt="Show revenue by region",
            data_source={"id": "ds-1", "name": "Oracle Sales", "type": "oracle", "database": "testing"},
            tenant_id="tenant-a",
        )
    )

    assert result.valid is True
    assert "FETCH FIRST 100 ROWS ONLY" in result.sql
    assert any("deterministic row-limit guard" in note for note in result.planner_notes)
