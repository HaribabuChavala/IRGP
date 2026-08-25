import os

import httpx


def read_secret_field(secret_path: str, field_name: str) -> str | None:
    vault_addr = os.getenv("VAULT_ADDR", "").strip()
    vault_token = os.getenv("VAULT_TOKEN", "").strip()
    if not vault_addr or not vault_token or not secret_path or not field_name:
        return None

    url = f"{vault_addr.rstrip('/')}/v1/{secret_path.lstrip('/')}"
    headers = {"X-Vault-Token": vault_token}

    with httpx.Client(timeout=10) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        body = response.json()

    # KV v2: {"data": {"data": {...}}}
    data = body.get("data")
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        value = data["data"].get(field_name)
        return str(value).strip() if value is not None else None

    # KV v1 compatibility: {"data": {...}}
    if isinstance(data, dict):
        value = data.get(field_name)
        return str(value).strip() if value is not None else None

    return None