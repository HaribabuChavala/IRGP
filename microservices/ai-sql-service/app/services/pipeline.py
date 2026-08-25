import re
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx

from app.config import settings

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


class SqlAgentPipeline:
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
            "oracle": ["customers", "sales_orders"],
            "teradata": ["customers", "sales_orders"],
            "hive": ["events", "sessions", "users"],
            "excel": ["sheet1"],
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

        selected_columns = "customer_id, customer_name, region"
        if "sales" in text:
            selected_columns = "order_id, customer_id, order_date, region"
        return f"SELECT {limit_prefix}{selected_columns} FROM {customers_table if 'customer' in text else sales_table}{limit_suffix}"

    def _contains_wildcard_select(self, sql: str) -> bool:
        select_match = re.search(r"\bselect\b(.*?)\bfrom\b", sql, flags=re.IGNORECASE | re.DOTALL)
        if not select_match:
            return False

        select_clause = select_match.group(1)
        select_clause = re.sub(r"count\s*\(\s*\*\s*\)", "count(__all__)", select_clause, flags=re.IGNORECASE)
        if "*" in select_clause:
            return True

        return bool(re.search(r"\b[a-zA-Z0-9_\"\.]+\.\*\b", select_clause, flags=re.IGNORECASE))

    def _extract_limit_values(self, sql: str) -> list[int]:
        values: list[int] = []
        values.extend(int(v) for v in re.findall(r"\blimit\s+(\d+)\b", sql, flags=re.IGNORECASE))
        values.extend(int(v) for v in re.findall(r"\bfetch\s+first\s+(\d+)\s+rows\s+only\b", sql, flags=re.IGNORECASE))
        values.extend(int(v) for v in re.findall(r"\bselect\s+top\s+(\d+)\b", sql, flags=re.IGNORECASE))
        return values

    def _has_aggregation(self, sql: str) -> bool:
        return bool(re.search(r"\b(count|sum|avg|min|max)\s*\(", sql, flags=re.IGNORECASE))

    def _table_allowed_for_tenant(self, table_name: str, tenant_allowlist: set[str]) -> bool:
        if table_name in tenant_allowlist:
            return True

        short_name = table_name.split(".")[-1]
        for item in tenant_allowlist:
            if item.endswith(".*") and table_name.startswith(item[:-1]):
                return True
            if item.split(".")[-1] == short_name:
                return True
        return False

    def _validate_sql(self, sql: str, schema_context: dict, tenant_id: str) -> tuple[bool, list[str]]:
        errors: list[str] = []
        normalized = re.sub(r"\s+", " ", sql.strip()).lower()

        if not (normalized.startswith("select") or normalized.startswith("with")):
            errors.append("Only SELECT statements are allowed")

        for op in FORBIDDEN_SQL_OPERATIONS:
            if re.search(rf"\b{re.escape(op)}\b", normalized):
                errors.append(f"Forbidden operation detected: {op.upper()}")

        if settings.deny_star_select and self._contains_wildcard_select(sql):
            errors.append("Wildcard SELECT is forbidden; select explicit columns only")

        limit_values = self._extract_limit_values(sql)
        if settings.enforce_row_limit and not self._has_aggregation(sql) and not limit_values:
            errors.append(f"Row limit is required and must be <= {settings.max_sql_limit}")
        for limit_value in limit_values:
            if limit_value > settings.max_sql_limit:
                errors.append(f"Row limit {limit_value} exceeds max allowed {settings.max_sql_limit}")

        refs = re.findall(r"\b(?:from|join)\s+([a-zA-Z0-9_\.\"]+)", sql, flags=re.IGNORECASE)
        schema_allowlist = schema_context["allow_list"]
        tenant_allowlist = set(settings.tenant_table_allowlist.get(tenant_id, []))
        if settings.require_tenant_allowlist and not tenant_allowlist:
            errors.append(f"Tenant {tenant_id} has no explicit table allow-list")

        for ref in refs:
            clean_ref = ref.replace('"', "")
            short_name = clean_ref.split(".")[-1]
            allowed_by_schema = clean_ref in schema_allowlist or any(item.split(".")[-1] == short_name for item in schema_allowlist)
            if not allowed_by_schema:
                errors.append(f"Table not allowed by policy: {clean_ref}")
            if tenant_allowlist and not self._table_allowed_for_tenant(clean_ref, tenant_allowlist):
                errors.append(f"Table not in tenant allow-list: {clean_ref}")

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

    def _needs_wildcard_retry(self, provider: str, validation_errors: list[str]) -> bool:
        if provider != "google-gemini-api":
            return False
        return any("Wildcard SELECT" in item for item in validation_errors)

    def _build_wildcard_correction_prompt(self, prompt: str, sql: str) -> str:
        return (
            f"{prompt}\n\n"
            "Previous output violated policy because it used wildcard selection. "
            "Regenerate SQL with explicit column names only. "
            "Never use SELECT * or alias.* in any clause.\n"
            f"Previous SQL:\n{sql}"
        )

    def _needs_row_limit_guard(self, validation_errors: list[str]) -> bool:
        return any("Row limit is required" in item for item in validation_errors)

    def _apply_row_limit_guard(self, sql: str, dialect: str) -> str | None:
        if self._extract_limit_values(sql):
            return None
        if self._has_aggregation(sql):
            return None

        max_limit = max(1, settings.max_sql_limit)
        base_sql = sql.strip().rstrip(";")

        if dialect == "oracle":
            return f"{base_sql} FETCH FIRST {max_limit} ROWS ONLY"

        if dialect == "teradata":
            if re.search(r"^\s*select\s+", base_sql, flags=re.IGNORECASE):
                return re.sub(
                    r"^\s*select\s+",
                    f"SELECT TOP {max_limit} ",
                    base_sql,
                    count=1,
                    flags=re.IGNORECASE,
                )
            return None

        return f"{base_sql} LIMIT {max_limit}"

    def _repair_wildcard_sql(self, sql: str, schema_context: dict) -> str | None:
        if not self._contains_wildcard_select(sql):
            return None

        normalized = re.sub(r"\s+", " ", sql.strip())
        reserved_alias_tokens = {
            "where",
            "join",
            "group",
            "order",
            "having",
            "limit",
            "fetch",
            "offset",
            "union",
            "inner",
            "left",
            "right",
            "full",
            "cross",
        }
        match = re.search(r"\b(from|join)\s+([a-zA-Z0-9_\.\"]+)", normalized, flags=re.IGNORECASE)
        if not match:
            return None

        table_ref = match.group(2).replace('"', "")
        table_name = table_ref
        alias_match = re.search(rf"\bfrom\s+{re.escape(match.group(2))}\s+([a-zA-Z0-9_]+)", normalized, flags=re.IGNORECASE)
        alias = alias_match.group(1) if alias_match else ""
        if alias.lower() in reserved_alias_tokens:
            alias = ""

        columns = schema_context.get("columns", {}).get(table_name)
        if not columns:
            short_table = table_name.split(".")[-1]
            for key, value in schema_context.get("columns", {}).items():
                if key.split(".")[-1] == short_table:
                    columns = value
                    table_name = key
                    break

        if not columns:
            return None

        explicit = ", ".join(f"{alias}.{col}" if alias else col for col in columns[:4])
        repaired = re.sub(r"\bselect\b\s+.*?\bfrom\b", f"SELECT {explicit} FROM", normalized, count=1, flags=re.IGNORECASE)
        return repaired

    def _extract_sql_from_text(self, text: str) -> str | None:
        if not text:
            return None

        code_block = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
        if code_block:
            candidate = code_block.group(1).strip()
            if candidate:
                return candidate

        sql_match = re.search(r"\b(select|with)\b[\s\S]*", text, flags=re.IGNORECASE)
        if sql_match:
            return sql_match.group(0).strip()

        return None

    def _extract_sql_from_gemini_response(self, body: dict) -> str | None:
        candidates = body.get("candidates")
        if not isinstance(candidates, list):
            return None

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content")
            if not isinstance(content, dict):
                continue
            parts = content.get("parts")
            if not isinstance(parts, list):
                continue

            text_chunks: list[str] = []
            for part in parts:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    text_chunks.append(part["text"])

            sql = self._extract_sql_from_text("\n".join(text_chunks).strip())
            if sql:
                return sql

        return None

    async def _generate_via_google_adk(self, payload: dict) -> tuple[str, str] | None:
        if not settings.google_adk_agent_url:
            return None

        raw_url = settings.google_adk_agent_url.strip()
        use_gemini_api = "generativelanguage.googleapis.com" in raw_url

        headers = {"Content-Type": "application/json"}
        request_url = raw_url
        request_payload: dict = payload

        provider_name = "google-adk-remote"
        if use_gemini_api:
            provider_name = "google-gemini-api"
            if ":generateContent" not in request_url:
                request_url = f"{request_url.rstrip('/')}/models/{settings.google_gemini_model}:generateContent"

            if settings.google_adk_agent_api_key:
                separator = "&" if "?" in request_url else "?"
                request_url = f"{request_url}{separator}key={quote_plus(settings.google_adk_agent_api_key)}"

            schema = payload.get("schema_context", {})
            policy = payload.get("policy", {})
            prompt_text = (
                "Generate exactly one read-only SQL query. Return only SQL.\n"
                f"User prompt: {payload.get('prompt', '')}\n"
                f"SQL dialect: {payload.get('dialect', 'ansi')}\n"
                f"Allowed tables: {schema.get('tables', [])}\n"
                f"Forbidden operations: {policy.get('forbidden_operations', [])}\n"
                "Never use SELECT * or alias.*; always select explicit columns.\n"
                "Do not include comments or explanations."
            )
            request_payload = {
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {"temperature": 0.1},
            }
        else:
            if settings.google_adk_agent_api_key:
                headers["Authorization"] = f"Bearer {settings.google_adk_agent_api_key}"

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(request_url, json=request_payload, headers=headers)
            response.raise_for_status()
            body = response.json()

        if provider_name == "google-gemini-api":
            sql = self._extract_sql_from_gemini_response(body)
        else:
            sql = body.get("sql") or body.get("query")

        if not sql:
            raise ValueError("Google ADK response missing sql/query field")
        return str(sql), provider_name

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

        provider = "ai-sql-service-local-fallback"
        remote_result = await self._generate_via_google_adk(payload)
        if remote_result is None:
            sql = self._generate_sql_local(prompt, data_source, schema_context)
        else:
            sql, provider = remote_result

        valid, validation_errors = self._validate_sql(sql, schema_context, tenant_id)
        if self._needs_wildcard_retry(provider, validation_errors):
            planner_notes.append("Retried generation to enforce explicit column selection")
            retry_payload = dict(payload)
            retry_payload["prompt"] = self._build_wildcard_correction_prompt(prompt, sql)
            retry_result = await self._generate_via_google_adk(retry_payload)
            if retry_result is not None:
                sql, provider = retry_result
                valid, validation_errors = self._validate_sql(sql, schema_context, tenant_id)

        if not valid and any("Wildcard SELECT" in item for item in validation_errors):
            repaired_sql = self._repair_wildcard_sql(sql, schema_context)
            if repaired_sql:
                planner_notes.append("Applied deterministic wildcard repair using schema columns")
                sql = repaired_sql
                valid, validation_errors = self._validate_sql(sql, schema_context, tenant_id)

        if not valid and self._needs_row_limit_guard(validation_errors):
            limited_sql = self._apply_row_limit_guard(sql, dialect)
            if limited_sql:
                planner_notes.append("Applied deterministic row-limit guard")
                sql = limited_sql
                valid, validation_errors = self._validate_sql(sql, schema_context, tenant_id)

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


pipeline = SqlAgentPipeline()
