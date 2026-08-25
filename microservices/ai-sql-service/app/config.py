import json
import os

from app.vault_client import read_secret_field


class Settings:
    google_adk_agent_url: str
    google_adk_agent_api_key: str
    google_gemini_model: str
    vault_secret_path: str
    vault_google_adk_api_key_field: str
    max_sql_limit: int
    deny_star_select: bool
    enforce_row_limit: bool
    require_tenant_allowlist: bool
    tenant_table_allowlist: dict[str, list[str]]

    @staticmethod
    def _as_bool(value: str, default: bool) -> bool:
        normalized = (value or "").strip().lower()
        if not normalized:
            return default
        return normalized in {"1", "true", "yes", "on"}

    @staticmethod
    def _as_int(value: str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _load_tenant_allowlist(value: str) -> dict[str, list[str]]:
        if not value.strip():
            return {
                "tenant-demo": [
                    "testing.sales_orders",
                    "testing.sales_order_items",
                    "testing.customers",
                    "testing.products",
                    "report_platform.sales_orders",
                    "report_platform.sales_order_items",
                    "report_platform.customers",
                    "report_platform.products",
                ],
                "tenant-acme": [
                    "testing.sales_orders",
                    "testing.sales_order_items",
                    "testing.customers",
                    "testing.products",
                    "report_platform.sales_orders",
                    "report_platform.sales_order_items",
                    "report_platform.customers",
                    "report_platform.products",
                ],
                "tenant-1": [
                    "testing.sales_orders",
                    "testing.sales_order_items",
                    "testing.customers",
                    "testing.products",
                    "report_platform.sales_orders",
                    "report_platform.sales_order_items",
                    "report_platform.customers",
                    "report_platform.products",
                ],
                "org-spartexai": [
                    "testing.sales_orders",
                    "testing.sales_order_items",
                    "testing.customers",
                    "testing.products",
                    "report_platform.sales_orders",
                    "report_platform.sales_order_items",
                    "report_platform.customers",
                    "report_platform.products",
                ],
                "bbe41162-bb3c-4d02-b0fc-ce48d7905d33": [
                    "testing.sales_orders",
                    "testing.sales_order_items",
                    "testing.customers",
                    "testing.products",
                    "report_platform.sales_orders",
                    "report_platform.sales_order_items",
                    "report_platform.customers",
                    "report_platform.products",
                ],
            }

        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}

        allowlist: dict[str, list[str]] = {}
        if isinstance(parsed, dict):
            for tenant_id, tables in parsed.items():
                if isinstance(tenant_id, str) and isinstance(tables, list):
                    allowlist[tenant_id] = [str(table).strip() for table in tables if str(table).strip()]
        return allowlist

    def __init__(self) -> None:
        raw_adk_url = os.getenv("GOOGLE_ADK_AGENT_URL", "").strip()
        if not raw_adk_url:
            raw_adk_url = "http://google-adk-agent:8001/agent"
        self.google_adk_agent_url = raw_adk_url

        self.vault_secret_path = os.getenv("VAULT_SECRET_PATH", "secret/data/report-platform").strip()
        self.vault_google_adk_api_key_field = os.getenv("VAULT_GOOGLE_ADK_API_KEY_FIELD", "GOOGLE_ADK_AGENT_API_KEY").strip()
        self.google_adk_agent_api_key = os.getenv("GOOGLE_ADK_AGENT_API_KEY", "local-adk-test-key").strip() or "local-adk-test-key"

        if "generativelanguage.googleapis.com" in self.google_adk_agent_url and not self.google_adk_agent_api_key:
            self.google_adk_agent_url = "http://google-adk-agent:8001/agent"

        if "generativelanguage.googleapis.com" in self.google_adk_agent_url:
            try:
                vault_key = read_secret_field(self.vault_secret_path, self.vault_google_adk_api_key_field)
            except Exception:
                vault_key = None
            if vault_key:
                self.google_adk_agent_api_key = vault_key

        self.google_gemini_model = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        self.max_sql_limit = self._as_int(os.getenv("MAX_SQL_LIMIT", "1000"), 1000)
        self.deny_star_select = self._as_bool(os.getenv("DENY_STAR_SELECT", "true"), True)
        self.enforce_row_limit = self._as_bool(os.getenv("ENFORCE_ROW_LIMIT", "true"), True)
        self.require_tenant_allowlist = self._as_bool(os.getenv("REQUIRE_TENANT_ALLOWLIST", "true"), True)
        self.tenant_table_allowlist = self._load_tenant_allowlist(os.getenv("TENANT_TABLE_ALLOWLIST_JSON", ""))


settings = Settings()
