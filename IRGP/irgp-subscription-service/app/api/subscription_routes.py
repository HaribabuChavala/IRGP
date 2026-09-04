from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import SubscriptionPlan
from app.schemas import PlansResponse, SubscriptionResponse, UpgradeRequest
from app.security import require_org_admin

router = APIRouter(tags=["subscriptions"])

AVAILABLE_PLANS = ["free", "pro", "enterprise"]


@router.get("/api/v1/subscriptions/plans", response_model=PlansResponse)
def list_plans() -> PlansResponse:
    return PlansResponse(plans=AVAILABLE_PLANS)


@router.get("/api/v1/organizations/{organization_id}/subscription", response_model=SubscriptionResponse)
def current_subscription(
    organization_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_org_admin)],
) -> SubscriptionResponse:
    plan = db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.organization_id == organization_id).order_by(SubscriptionPlan.created_at.desc())
    )
    if not plan:
        return SubscriptionResponse(organization_id=organization_id, plan="free")
    return SubscriptionResponse(organization_id=organization_id, plan=plan.plan, status=plan.status)


@router.post("/api/v1/organizations/{organization_id}/subscription/upgrade", response_model=SubscriptionResponse)
def upgrade_subscription(
    organization_id: str,
    payload: UpgradeRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_org_admin)],
) -> SubscriptionResponse:
    if payload.plan not in AVAILABLE_PLANS:
        raise HTTPException(status_code=400, detail="Unsupported plan")

    plan = db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.organization_id == organization_id).order_by(SubscriptionPlan.created_at.desc())
    )
    if plan is None:
        plan = SubscriptionPlan(id=str(uuid.uuid4()), organization_id=organization_id, plan=payload.plan, status="active")
        db.add(plan)
    else:
        plan.plan = payload.plan
        plan.status = "active"

    db.commit()
    db.refresh(plan)
    return SubscriptionResponse(organization_id=organization_id, plan=plan.plan, status=plan.status)
