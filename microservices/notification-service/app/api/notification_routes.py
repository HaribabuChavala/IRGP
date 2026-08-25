from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Notification
from app.schemas import NotificationCreateRequest, NotificationListResponse, NotificationResponse
from app.security import require_org_admin

router = APIRouter(tags=["notifications"])


@router.get("/api/v1/notifications", response_model=NotificationListResponse)
def list_notifications(
    organization_id: str = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_org_admin),
) -> NotificationListResponse:
    rows = db.scalars(
        select(Notification).where(Notification.organization_id == organization_id).order_by(Notification.created_at.desc())
    ).all()
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=row.id,
                organization_id=row.organization_id,
                message=row.message,
                type=row.type,
                read=row.read,
            )
            for row in rows
        ]
    )


@router.post("/api/v1/notifications", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_org_admin)],
) -> Notification:
    item = Notification(
        id=str(uuid.uuid4()),
        organization_id=payload.organization_id,
        message=payload.message,
        type=payload.type.upper(),
        read=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/api/v1/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_org_admin)],
) -> Notification:
    item = db.get(Notification, notification_id)
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.read = True
    db.commit()
    db.refresh(item)
    return item
