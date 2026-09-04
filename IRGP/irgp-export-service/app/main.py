from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.security import require_org_admin

app = FastAPI(title="Export Service", version="1.0.0")

_exports: list[dict[str, Any]] = []


class ExportCreate(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    report_id: str = Field(min_length=1, max_length=64)
    format: str = Field(min_length=1, max_length=16)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "export-service"}


@app.get("/api/v1/exports")
async def list_exports(
    organization_id: str = Query(...),
    _: dict = Depends(require_org_admin),
) -> dict[str, list[dict[str, Any]]]:
    return {"exports": [item for item in _exports if item["organization_id"] == organization_id]}


@app.post("/api/v1/exports", status_code=status.HTTP_201_CREATED)
async def create_export(
    payload: ExportCreate,
    _: dict = Depends(require_org_admin),
) -> dict[str, Any]:
    export = {
        "id": str(uuid.uuid4()),
        "organization_id": payload.organization_id,
        "report_id": payload.report_id,
        "format": payload.format,
        "status": "queued",
    }
    _exports.append(export)
    return export


@app.get("/api/v1/exports/{export_id}")
async def get_export(
    export_id: str,
    _: dict = Depends(require_org_admin),
) -> dict[str, Any]:
    for item in _exports:
        if item["id"] == export_id:
            return item
    raise HTTPException(status_code=404, detail="Export not found")
