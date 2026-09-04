from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, FastAPI, Query, status
from pydantic import BaseModel, Field

from app.security import require_platform_admin

app = FastAPI(title="Observability Service", version="1.0.0")

_observability_events: list[dict[str, Any]] = []


class EventCreate(BaseModel):
    service_name: str = Field(min_length=1, max_length=128)
    level: str = Field(default="INFO", min_length=1, max_length=32)
    message: str = Field(min_length=1, max_length=1000)
    details: dict[str, Any] = Field(default_factory=dict)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "observability-service"}


@app.get("/api/v1/observability/events")
async def list_observability_events(
    service_name: str | None = Query(default=None),
    _: dict = Depends(require_platform_admin),
) -> dict[str, list[dict[str, Any]]]:
    events = _observability_events
    if service_name:
        events = [event for event in events if event["service_name"] == service_name]
    return {"events": events}


@app.post("/api/v1/observability/events", status_code=status.HTTP_201_CREATED)
async def create_observability_event(
    payload: EventCreate,
    _: dict = Depends(require_platform_admin),
) -> dict[str, Any]:
    event = {
        "id": str(uuid.uuid4()),
        "service_name": payload.service_name,
        "level": payload.level,
        "message": payload.message,
        "details": payload.details,
    }
    _observability_events.append(event)
    return event
