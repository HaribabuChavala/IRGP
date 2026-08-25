from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, FastAPI, Query, status
from pydantic import BaseModel, Field

from app.security import require_org_admin

app = FastAPI(title="Scheduler Service", version="1.0.0")

_schedules: list[dict[str, Any]] = []


class ScheduleCreate(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=1, max_length=128)
    cron_expression: str = Field(min_length=1, max_length=64)
    target_type: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=64)
    status: str = Field(default="active", min_length=1, max_length=32)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "scheduler-service"}


@app.get("/api/v1/schedules")
async def list_schedules(
    organization_id: str = Query(...),
    _: dict = Depends(require_org_admin),
) -> dict[str, list[dict[str, Any]]]:
    return {"schedules": [schedule for schedule in _schedules if schedule["organization_id"] == organization_id]}


@app.post("/api/v1/schedules", status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreate,
    _: dict = Depends(require_org_admin),
) -> dict[str, Any]:
    schedule = {
        "id": str(uuid.uuid4()),
        "organization_id": payload.organization_id,
        "name": payload.name,
        "cron_expression": payload.cron_expression,
        "target_type": payload.target_type,
        "target_id": payload.target_id,
        "status": payload.status,
    }
    _schedules.append(schedule)
    return schedule
