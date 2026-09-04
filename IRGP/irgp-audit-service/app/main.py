from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, FastAPI, Query, status
from pydantic import BaseModel, Field

from app.security import require_org_admin

app = FastAPI(title="Audit Service", version="1.0.0")

_audit_events: list[dict[str, Any]] = []


class AuditEventCreate(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    actor_id: str = Field(min_length=1, max_length=64)
    entity_type: str = Field(min_length=1, max_length=64)
    entity_id: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=64)
    details: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "audit-service"}


@app.get("/api/v1/audit")
async def list_audit_events(
    organization_id: str = Query(...),
    _: dict = Depends(require_org_admin),
) -> dict[str, list[dict[str, Any]]]:
    return {"events": [event for event in _audit_events if event["organization_id"] == organization_id]}


@app.post("/api/v1/audit", status_code=status.HTTP_201_CREATED)
async def create_audit_event(
    payload: AuditEventCreate,
    _: dict = Depends(require_org_admin),
) -> dict[str, Any]:
    event = {
        "id": str(uuid.uuid4()),
        "organization_id": payload.organization_id,
        "actor_id": payload.actor_id,
        "entity_type": payload.entity_type,
        "entity_id": payload.entity_id,
        "action": payload.action,
        "details": payload.details,
    }
    _audit_events.append(event)
    return event
