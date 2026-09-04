from __future__ import annotations

import secrets
import string
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.email_service import send_temp_password_email
from app.models import Organization, User
from app.schemas import (
    OrganizationCreateRequest,
    OrganizationOnboardRequest,
    OrganizationOnboardingResponse,
    OrganizationResponse,
    OrganizationSummaryResponse,
    OnboardingUserResponse,
)
from app.security import require_platform_admin

router = APIRouter(prefix="/api/v1/admin/organizations", tags=["organization-registration"])


def generate_temporary_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
) -> Organization:
    existing = db.scalar(select(Organization).where(Organization.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Organization name already exists")

    org = Organization(
        id=str(uuid.uuid4()),
        name=payload.name,
        contact_email=payload.contact_email.lower(),
        region=payload.region,
        plan=payload.plan,
        status="active",
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.post("/onboard", response_model=OrganizationOnboardingResponse, status_code=status.HTTP_201_CREATED)
def onboard_organization(
    payload: OrganizationOnboardRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
) -> OrganizationOnboardingResponse:
    if db.scalar(select(Organization).where(Organization.name == payload.organization_name.strip())):
        raise HTTPException(status_code=409, detail="Organization name already exists")

    org = Organization(
        id=str(uuid.uuid4()),
        name=payload.organization_name.strip(),
        contact_email=payload.contact_email.lower(),
        region=payload.region,
        plan=payload.plan,
        status="active",
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    invited_users = [payload.organization_admin, *payload.users]
    created_users: list[OnboardingUserResponse] = []
    for invited_user in invited_users:
        normalized_email = invited_user.email.lower()
        if db.scalar(select(User).where(User.email == normalized_email)):
            raise HTTPException(status_code=409, detail=f"User email already exists: {normalized_email}")

        temp_password = generate_temporary_password()
        user = User(
            id=str(uuid.uuid4()),
            email=normalized_email,
            username=invited_user.username,
            full_name=invited_user.full_name or invited_user.username,
            organization_id=org.id,
            role=invited_user.role,
            status="active",
            password_hash=__import__("hashlib").sha256(temp_password.encode("utf-8")).hexdigest(),
            force_password_reset=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        send_temp_password_email(
            recipient=user.email,
            username=user.username,
            temp_password=temp_password,
            organization_name=org.name,
        )

        created_users.append(
            OnboardingUserResponse(
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                force_password_reset=user.force_password_reset,
                temporary_password=temp_password,
            )
        )

    return OrganizationOnboardingResponse(
        organization=OrganizationSummaryResponse(
            id=org.id,
            name=org.name,
            contact_email=org.contact_email,
            region=org.region,
            plan=org.plan,
            status=org.status,
        ),
        created_users=created_users,
        email_delivery="queued",
    )


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
    q: str | None = Query(default=None, alias="query"),
) -> list[Organization]:
    stmt = select(Organization)
    if q:
        stmt = stmt.where(Organization.name.ilike(f"%{q}%"))
    return list(db.scalars(stmt.order_by(Organization.created_at.desc())).all())


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
) -> Organization:
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: str,
    payload: OrganizationCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
) -> Organization:
    org = db.get(Organization, organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.name = payload.name
    org.contact_email = payload.contact_email.lower()
    org.region = payload.region
    org.plan = payload.plan
    db.commit()
    db.refresh(org)
    return org
