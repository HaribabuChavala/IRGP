import hashlib
import json
import os
import time

import httpx
import jwt
import redis
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient

OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "http://localhost:8081/realms/report-platform")
KEYCLOAK_JWKS_URL = os.getenv(
    "KEYCLOAK_JWKS_URL",
    "http://keycloak:8080/realms/report-platform/protocol/openid-connect/certs",
)
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "dev-root-token")
VAULT_SECRET_PATH = os.getenv("VAULT_SECRET_PATH", "secret/data/report-platform")

redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True,
)

CACHE_TTL = 60
AUDIT_LOG_KEY = "audit:denied"

security = HTTPBearer()
jwks_client = PyJWKClient(KEYCLOAK_JWKS_URL)


class SecurityContext:
    def __init__(self, payload: dict):
        self.user_id = payload.get("sub")
        self.username = payload.get("preferred_username")
        self.email = payload.get("email")
        self.roles = payload.get("realm_access", {}).get("roles", [])

        fallback = self._resolve_identity_context()
        self.tenant_id = (
            payload.get("tenant_id")
            or payload.get("organization_id")
            or payload.get("org_id")
            or fallback.get("tenant_id")
            or ""
        )
        self.region = payload.get("region") or fallback.get("region") or ""
        self.organization_name = payload.get("organization_name") or fallback.get("organization_name") or ""

    def _resolve_identity_context(self) -> dict:
        identity = {"tenant_id": "", "region": "", "organization_name": ""}
        if not any([self.user_id, self.email, self.username]):
            return identity

        try:
            from database import SessionLocal
            from models import User

            with SessionLocal() as db:
                user_record = None
                if self.user_id:
                    user_record = (
                        db.query(User)
                        .filter((User.keycloak_user_id == self.user_id) | (User.id == self.user_id))
                        .first()
                    )
                if user_record is None and self.email:
                    user_record = db.query(User).filter(User.email.ilike(self.email)).first()
                if user_record is None and self.username:
                    user_record = db.query(User).filter(User.username.ilike(self.username)).first()
                if user_record is not None:
                    identity["tenant_id"] = user_record.tenant_id or user_record.organization_id or ""
                    identity["region"] = user_record.region or ""
                    identity["organization_name"] = user_record.organization_name or ""
        except Exception:
            return identity

        return identity

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "tenant_id": self.tenant_id,
            "region": self.region,
            "organization_name": self.organization_name,
        }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> SecurityContext:
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=KEYCLOAK_ISSUER,
            options={"verify_aud": False},
        )
        return SecurityContext(payload)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid access token: {str(exc)}") from exc


def require_platform_admin(user: SecurityContext) -> None:
    if "PLATFORM_ADMIN" not in user.roles:
        raise HTTPException(status_code=403, detail="Platform admin access required")


def require_org_admin(user: SecurityContext) -> None:
    if "REPORT_ADMIN" not in user.roles and "PLATFORM_ADMIN" not in user.roles:
        raise HTTPException(status_code=403, detail="Organization admin access required")


async def check_policy(user: SecurityContext, resource: dict, action: str) -> bool:
    cache_key = "policy:" + hashlib.sha256(
        json.dumps({"user_id": user.user_id, "resource": resource, "action": action}, sort_keys=True).encode()
    ).hexdigest()

    cached = redis_client.get(cache_key)
    if cached is not None:
        return cached == "true"

    opa_input = {"input": {"user": user.to_dict(), "resource": resource, "action": action}}

    async with httpx.AsyncClient(timeout=5) as client:
        try:
            response = await client.post(f"{OPA_URL}/v1/data/report/authz/allow", json=opa_input)
            result = response.json().get("result", False) if response.status_code == 200 else False
        except Exception:
            result = False

    redis_client.set(cache_key, str(result).lower(), ex=CACHE_TTL)
    return result


def log_denied_access(user: SecurityContext, resource: dict, action: str) -> None:
    entry = {
        "timestamp": time.time(),
        "user_id": user.user_id,
        "username": user.username,
        "roles": user.roles,
        "tenant_id": user.tenant_id,
        "region": user.region,
        "resource": resource,
        "action": action,
    }
    redis_client.lpush(AUDIT_LOG_KEY, json.dumps(entry))
    redis_client.ltrim(AUDIT_LOG_KEY, 0, 999)

    try:
        from database import SessionLocal
        from models import AuditEvent

        with SessionLocal() as db:
            db.add(
                AuditEvent(
                    organization_id=user.tenant_id or None,
                    user_id=None,
                    username=user.username,
                    user_roles={"roles": user.roles},
                    tenant_id=user.tenant_id or None,
                    region=user.region or None,
                    resource_type=resource.get("type") if isinstance(resource, dict) else None,
                    resource_id=resource.get("id") if isinstance(resource, dict) else None,
                    resource=resource if isinstance(resource, dict) else {},
                    action=action,
                    decision="DENIED",
                    reason="Access denied by policy evaluation",
                )
            )
            db.commit()
    except Exception:
        pass


async def get_vault_secret(path: str | None = None) -> dict:
    url = f"{VAULT_ADDR}/v1/{path or VAULT_SECRET_PATH}"
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(url, headers={"X-Vault-Token": VAULT_TOKEN})
    if response.status_code == 200:
        return response.json().get("data", {}).get("data", {})
    if response.status_code == 404:
        return {}
    raise Exception(f"Vault error: {response.status_code} - {response.text}")
