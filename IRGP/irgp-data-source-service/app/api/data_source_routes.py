from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DataSource
from app.schemas import DataSourceCreateRequest, DataSourceListResponse, DataSourceResponse
from app.security import require_org_admin

router = APIRouter(tags=["data-sources"])


@router.get("/api/v1/data-sources", response_model=DataSourceListResponse)
def list_data_sources(
    organization_id: str = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_org_admin),
) -> DataSourceListResponse:
    rows = db.scalars(
        select(DataSource).where(DataSource.organization_id == organization_id).order_by(DataSource.created_at.desc())
    ).all()
    return DataSourceListResponse(
        data_sources=[
            DataSourceResponse(
                id=row.id,
                organization_id=row.organization_id,
                name=row.name,
                type=row.type,
                connection_string=row.connection_string,
                status=row.status,
            )
            for row in rows
        ]
    )


@router.post("/api/v1/data-sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def create_data_source(
    payload: DataSourceCreateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_org_admin),
) -> DataSource:
    source = DataSource(
        id=str(uuid.uuid4()),
        organization_id=payload.organization_id,
        name=payload.name,
        type=payload.type.lower(),
        connection_string=payload.connection_string,
        status="active",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
