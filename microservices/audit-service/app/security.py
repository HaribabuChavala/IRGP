from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_SECRET_KEY = "dev-secret-change-me"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
security = HTTPBearer()


def create_token(subject: str, payload: dict[str, Any], expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    token_payload = {"sub": subject, "iat": now, "exp": exp, **payload}
    return jwt.encode(token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(subject: str, payload: dict[str, Any]) -> str:
    return create_token(subject, payload, JWT_ACCESS_TOKEN_EXPIRE_MINUTES)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def require_org_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    payload = decode_token(credentials.credentials)
    roles = payload.get("roles", [])
    organization_id = payload.get("organization_id")
    if "ORG_ADMIN" not in roles and "PLATFORM_ADMIN" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admin access required")
    if not organization_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing organization identity")
    return payload
