import os
from urllib.parse import urlparse

import hvac


VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-root-token")
VAULT_SECRET_PATH = os.getenv("VAULT_SECRET_PATH", "secret/data/report-platform")


def _normalize_vault_path(raw_path: str | None = None) -> tuple[str, str]:
    value = (raw_path or VAULT_SECRET_PATH or "").strip().strip("/")
    if not value:
        return "secret", "report-platform"

    if value.startswith(("http://", "https://")):
        value = urlparse(value).path.strip("/")

    if value.startswith("v1/"):
        value = value[3:]

    parts = value.split("/")
    if len(parts) >= 3 and parts[0] == "secret" and parts[1] == "data":
        return "secret", "/".join(parts[2:]) or "report-platform"
    if len(parts) >= 2 and parts[0] == "secret":
        return "secret", "/".join(parts[1:]) or "report-platform"
    if len(parts) >= 2 and parts[1] == "data":
        return parts[0], "/".join(parts[2:]) or "report-platform"
    return "secret", value or "report-platform"


def get_vault_client():
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")
    return client


def get_secrets(path: str | None = None):
    client = get_vault_client()
    mount_point, secret_path = _normalize_vault_path(path)
    response = client.secrets.kv.v2.read_secret_version(path=secret_path, mount_point=mount_point)
    return response.get("data", {}).get("data", {})