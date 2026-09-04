from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DataSource
from app.schemas import DashboardResponse, DataSourceSummary, DataSourcesResponse
from app.security import require_org_admin

router = APIRouter(prefix="/api/v1/organizations/{organization_id}", tags=["org-portal"])


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    organization_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_org_admin)],
) -> DashboardResponse:
    rows = db.scalars(select(DataSource).where(DataSource.organization_id == organization_id)).all()
    return DashboardResponse(
        organization_id=organization_id,
        total_queries=0,
        data_source_count=len(rows),
        recent_executions=0,
    )


@router.get("/data-sources", response_model=DataSourcesResponse)
def data_sources(
    organization_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_org_admin)],
) -> DataSourcesResponse:
    rows = db.scalars(select(DataSource).where(DataSource.organization_id == organization_id).order_by(DataSource.created_at.desc())).all()
    return DataSourcesResponse(
        organization_id=organization_id,
        data_sources=[
            DataSourceSummary(id=row.id, name=row.name, type=row.type, status=row.status) for row in rows
        ],
    )
