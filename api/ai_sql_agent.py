import os
import re
from dataclasses import dataclass

import httpx


FORBIDDEN_SQL_OPERATIONS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "grant",
    "revoke",
    "merge",
    "exec",
    "execute",
    "create",
    "replace",
}


@dataclass
class SqlGenerationResult:
    sql: str
    dialect: str
    valid: bool
    validation_errors: list[str]
    estimated_cost: str
    pii_detected: bool
    pii_columns: list[str]
    planner_notes: list[str]
    provider: str


class GoogleAdkSqlAgentService:
    def __init__(self) -> None:
        self.sql_service_url = os.getenv("AI_SQL_SERVICE_URL", "http://ai-sql-service:8000/generate-sql").strip()
        self.agent_url = os.getenv("GOOGLE_ADK_AGENT_URL", "http://google-adk-agent:8001/agent").strip() or "http://google-adk-agent:8001/agent"
        self.agent_api_key = os.getenv("GOOGLE_ADK_AGENT_API_KEY", "local-adk-test-key").strip() or "local-adk-test-key"

    def _dialect_for_source(self, source_type: str) -> str:
        mapping = {
            "oracle": "oracle",
            "teradata": "teradata",
            "hive": "hive",
            "excel": "sqlite",
        }
        return mapping.get((source_type or "").lower(), "ansi")

    def _discover_schema(self, data_source: dict) -> dict:
        source_type = (data_source.get("type") or "").lower()
        if source_type == "oracle":
            schema_name = (data_source.get("schema") or "report_owner").strip() or "report_owner"
        elif source_type == "teradata":
            schema_name = (data_source.get("schema") or "public").strip() or "public"
        else:
            schema_name = (data_source.get("schema") or data_source.get("database") or "default").strip() or "default"

        tables_by_type = {
            "oracle": [
                "customers",
                "sales_orders",
            ],
            "teradata": [
                "customers",
                "sales_orders",
            ],
            "hive": [
                "events",
                "sessions",
                "users",
            ],
            "excel": [
                "sheet1",
            ],
        }

        columns = {
            "customers": ["customer_id", "customer_name", "region"],
            "sales_orders": ["order_id", "customer_id", "order_date", "region", "amount", "status"],
            "sales_order_items": ["order_id", "product_id", "quantity", "unit_price"],
            "products": ["product_id", "product_name", "category"],
            "fact_sales": ["sale_id", "customer_id", "product_id", "sale_date", "region", "revenue_amount"],
            "dim_customer": ["customer_id", "customer_name", "region"],
            "dim_product": ["product_id", "product_name", "category"],
            "dim_date": ["date_key", "month", "quarter", "year"],
            "events": ["event_time", "event_type", "user_id", "region"],
            "sessions": ["session_id", "user_id", "started_at", "duration_seconds"],
            "users": ["user_id", "user_name", "region", "email"],
            "sheet1": ["col1", "col2", "col3", "col4"],
        }

        tables = tables_by_type.get(source_type, ["dataset_table"])
        qualified_tables = [f"{schema_name}.{table}" for table in tables]
        allow_list = set(qualified_tables)

        return {
            "schema": schema_name,
            "tables": qualified_tables,
            "columns": {table: columns.get(table.split(".")[-1], ["id", "value"]) for table in qualified_tables},
            "allow_list": allow_list,
        }

    def _semantic_plan(self, prompt: str, schema_context: dict) -> list[str]:
        text = prompt.lower()
        plan = ["Map user intent to business metrics"]

        if "revenue" in text or "sales" in text:
            plan.append("Use aggregation on monetary columns")
        if "region" in text:
            plan.append("Group by region for segmented output")
        if "month" in text or "quarter" in text or "year" in text:
            plan.append("Apply time filter or period grouping")

        plan.append(f"Restrict to allowed tables ({len(schema_context['tables'])})")
        return plan

    def _limit_clause(self, dialect: str, limit: int = 100) -> tuple[str, str]:
        if dialect == "oracle":
            return "", f" FETCH FIRST {limit} ROWS ONLY"
        if dialect == "teradata":
            return f"TOP {limit} ", ""
        return "", f" LIMIT {limit}"

    def _generate_sql_local(self, prompt: str, data_source: dict, schema_context: dict) -> str:
        dialect = self._dialect_for_source(data_source.get("type", ""))
        limit_prefix, limit_suffix = self._limit_clause(dialect)
        tables = schema_context["tables"]
        table_map = {
            "customers": next((item for item in tables if item.lower().endswith("customers")), tables[0]),
            "sales_orders": next((item for item in tables if item.lower().endswith("sales_orders")), tables[-1]),
        }
        customers_table = table_map["customers"]
        sales_table = table_map["sales_orders"]
        text = prompt.lower()
        region_filter = ""
        if any(token in text for token in ("only us sales", "us sales", "sales in us", "in us", "usa", "united states")):
            region_filter = " WHERE c.region = 'US' "

        if "count" in text and "customer" in text:
            return f"SELECT COUNT(*) AS customer_count FROM {customers_table}"

        if "revenue" in text or "sales" in text:
            join_sql = (
                f"FROM {sales_table} so "
                f"JOIN {customers_table} c ON c.customer_id = so.customer_id "
                f"{region_filter}"
                f"GROUP BY c.region "
            )
            return (
                f"SELECT {limit_prefix}c.region AS region, SUM(so.amount) AS total_revenue "
                f"{join_sql}"
                f"ORDER BY total_revenue DESC{limit_suffix}"
            )

        if "top" in text and "product" in text:
            return (
                f"SELECT {limit_prefix}product_id, SUM(amount) AS total_revenue "
                f"FROM {sales_table} "
                f"GROUP BY product_id "
                f"ORDER BY total_revenue DESC{limit_suffix}"
            )

        return f"SELECT {limit_prefix}* FROM {sales_table}{limit_suffix}"

    def _validate_sql(self, sql: str, schema_context: dict) -> tuple[bool, list[str]]:
        errors: list[str] = []
        normalized = re.sub(r"\s+", " ", sql.strip()).lower()

        if not (normalized.startswith("select") or normalized.startswith("with")):
            errors.append("Only SELECT statements are allowed")

        for op in FORBIDDEN_SQL_OPERATIONS:
            if re.search(rf"\b{re.escape(op)}\b", normalized):
                errors.append(f"Forbidden operation detected: {op.upper()}")

        refs = re.findall(r"\b(?:from|join)\s+([a-zA-Z0-9_\.\"]+)", sql, flags=re.IGNORECASE)
        allow_list = schema_context["allow_list"]
        for ref in refs:
            clean_ref = ref.replace('"', "")
            if clean_ref not in allow_list:
                errors.append(f"Table not allowed by policy: {clean_ref}")

        return len(errors) == 0, errors

    def _estimate_cost(self, sql: str) -> str:
        text = sql.lower()
        joins = len(re.findall(r"\bjoin\b", text))
        group_by = 1 if "group by" in text else 0

        score = joins * 4 + group_by * 2
        if score <= 2:
            return "low"
        if score <= 6:
            return "medium"
        return "high"

    def _pii_scan(self, sql: str) -> tuple[bool, list[str]]:
        pii_patterns = ["email", "phone", "mobile", "ssn", "passport", "address"]
        lower_sql = sql.lower()
        hits = [name for name in pii_patterns if name in lower_sql]
        return len(hits) > 0, hits

    async def _generate_via_remote_adk(self, payload: dict) -> str | None:
        if not self.agent_url or not self.agent_api_key:
            return None

        headers = {"Content-Type": "application/json"}
        if self.agent_api_key:
            headers["Authorization"] = f"Bearer {self.agent_api_key}"
        # Support two ADK formats:
        # - legacy/adk mock: expects payload with 'question' and returns {'sql': ...}
        # - platform ADK style: receives our generic payload and returns {'sql': ...}
        url = self.agent_url.strip()

        # If the configured URL looks like the IRGP SQL Agent service, call its /api/v1/query
        if "irgp-sql-agent" in url or url.endswith("/api/v1/query") or url.endswith("/api/v1/query/"):
            target = url.rstrip('/')
            if not target.endswith('/api/v1/query'):
                target = target + '/api/v1/query'
            body = {
                "question": payload.get("prompt") or payload.get("question") or "",
                "session_id": payload.get("tenant_id") or "",
                "user_id": payload.get("user_id") or "system",
                "max_rows": payload.get("policy", {}).get("max_rows", 1000),
            }
        else:
            target = url
            body = payload

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(target, json=body, headers=headers)
            response.raise_for_status()
            body = response.json()

        sql = body.get("sql") or body.get("query")
        if not sql:
            # fallback: some ADK mocks return nested structures, try common places
            if isinstance(body, dict) and "result" in body and isinstance(body["result"], dict):
                sql = body["result"].get("sql")
        if not sql:
            raise ValueError("ADK agent response missing sql field: %r" % (body,))
        return str(sql)

    async def _generate_via_sql_service(self, payload: dict) -> SqlGenerationResult | None:
        if not self.sql_service_url:
            return None

        body = {
            "prompt": payload["prompt"],
            "tenant_id": payload["tenant_id"],
            "data_source": payload["data_source"],
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(self.sql_service_url, json=body, headers={"Content-Type": "application/json"})

        if response.status_code >= 400:
            raise ValueError(f"AI SQL service failed: {response.status_code} {response.text}")

        service_payload = response.json()
        return SqlGenerationResult(
            sql=str(service_payload.get("sql", "")),
            dialect=str(service_payload.get("dialect", "ansi")),
            valid=bool(service_payload.get("valid", False)),
            validation_errors=list(service_payload.get("validation_errors", [])),
            estimated_cost=str(service_payload.get("estimated_cost", "unknown")),
            pii_detected=bool(service_payload.get("pii_detected", False)),
            pii_columns=list(service_payload.get("pii_columns", [])),
            planner_notes=list(service_payload.get("planner_notes", [])),
            provider=str(service_payload.get("provider", "ai-sql-service")),
        )

    async def generate_sql(self, prompt: str, data_source: dict, tenant_id: str) -> SqlGenerationResult:
        dialect = self._dialect_for_source(data_source.get("type", ""))
        schema_context = self._discover_schema(data_source)
        planner_notes = self._semantic_plan(prompt, schema_context)

        payload = {
            "task": "generate_sql",
            "prompt": prompt,
            "dialect": dialect,
            "tenant_id": tenant_id,
            "data_source": {
                "id": data_source.get("id"),
                "name": data_source.get("name"),
                "type": data_source.get("type"),
                "database": data_source.get("database"),
            },
            "schema_context": {
                "schema": schema_context["schema"],
                "tables": schema_context["tables"],
                "columns": schema_context["columns"],
            },
            "policy": {
                "allow_only_select": True,
                "allowed_tables": schema_context["tables"],
                "forbidden_operations": sorted(FORBIDDEN_SQL_OPERATIONS),
            },
        }

        sql_service_result = await self._generate_via_sql_service(payload)
        if sql_service_result is not None:
            return sql_service_result

        provider = "google-adk-local-fallback"
        sql = await self._generate_via_remote_adk(payload)
        if sql is None:
            sql = self._generate_sql_local(prompt, data_source, schema_context)
        else:
            provider = "google-adk-remote"

        valid, validation_errors = self._validate_sql(sql, schema_context)
        estimated_cost = self._estimate_cost(sql)
        pii_detected, pii_columns = self._pii_scan(sql)

        return SqlGenerationResult(
            sql=sql,
            dialect=dialect,
            valid=valid,
            validation_errors=validation_errors,
            estimated_cost=estimated_cost,
            pii_detected=pii_detected,
            pii_columns=pii_columns,
            planner_notes=planner_notes,
            provider=provider,
        )


sql_agent_service = GoogleAdkSqlAgentService()
