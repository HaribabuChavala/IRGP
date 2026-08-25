from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Reminder
from app.schemas import ReminderCreateRequest, ReminderListResponse, ReminderResponse
from app.security import require_org_admin

router = APIRouter(tags=["reminders"])


@router.get("/api/v1/reminders", response_model=ReminderListResponse)
def list_reminders(
    organization_id: str = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(require_org_admin),
) -> ReminderListResponse:
    rows = db.scalars(
        select(Reminder).where(Reminder.organization_id == organization_id).order_by(Reminder.created_at.desc())
    ).all()
    return ReminderListResponse(
        reminders=[
            ReminderResponse(
                id=row.id,
                organization_id=row.organization_id,
                title=row.title,
                schedule=row.schedule,
                message=row.message,
                status=row.status,
            )
            for row in rows
        ]
    )


@router.post("/api/v1/reminders", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(
    payload: ReminderCreateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_org_admin),
) -> Reminder:
    reminder = Reminder(
        id=str(uuid.uuid4()),
        organization_id=payload.organization_id,
        title=payload.title,
        schedule=payload.schedule,
        message=payload.message,
        status="active",
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder
