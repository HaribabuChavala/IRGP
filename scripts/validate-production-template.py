#!/usr/bin/env python3
"""Validate .env.production.example contains required keys and safe placeholder values."""

from pathlib import Path
import sys

REQUIRED_KEYS = [
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "KEYCLOAK_ADMIN_USERNAME",
    "KEYCLOAK_ADMIN_PASSWORD",
    "KEYCLOAK_DB_USER",
    "KEYCLOAK_DB_PASSWORD",
    "VAULT_TOKEN",
    "VAULT_ADDR",
    "DATABASE_URL",
    "KEYCLOAK_ISSUER",
    "KEYCLOAK_JWKS_URL",
    "NEXT_PUBLIC_API_BASE_URL",
    "NEXT_PUBLIC_KEYCLOAK_URL",
    "GOOGLE_ADK_AGENT_URL",
]

SENSITIVE_TEMPLATE_KEYS = [
    "POSTGRES_PASSWORD",
    "KEYCLOAK_ADMIN_PASSWORD",
    "KEYCLOAK_DB_PASSWORD",
    "VAULT_ROOT_TOKEN",
    "VAULT_TOKEN",
    "GOOGLE_ADK_AGENT_API_KEY",
    "SMTP_PASSWORD",
    "SENDGRID_API_KEY",
    "JWT_SECRET_KEY",
    "MICROSERVICE_JWT_SECRET_KEY",
]

PLACEHOLDER_MARKERS = ("replace-with", "change-me")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def main() -> int:
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".env.production.example")
    if not env_path.exists():
        print(f"ERROR: Missing file: {env_path}")
        return 1

    data = parse_env_file(env_path)

    missing = [key for key in REQUIRED_KEYS if key not in data or not data[key]]
    if missing:
        print("ERROR: Missing required keys:")
        for key in missing:
            print(f" - {key}")

    weak_sensitive = []
    for key in SENSITIVE_TEMPLATE_KEYS:
        value = data.get(key, "")
        if not value:
            continue
        lowered = value.lower()
        if not any(marker in lowered for marker in PLACEHOLDER_MARKERS):
            weak_sensitive.append((key, value))

    if weak_sensitive:
        print("ERROR: Sensitive template keys should use placeholder values, not real secrets:")
        for key, value in weak_sensitive:
            print(f" - {key}={value}")

    if missing or weak_sensitive:
        return 1

    print(f"OK: {env_path} passed production template validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
