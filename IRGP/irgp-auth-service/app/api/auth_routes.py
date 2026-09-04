from __future__ import annotations

import secrets
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Organization, User
from app.schemas import (
    LoginRequest,
    OrganizationOnboardRequest,
    OrganizationOnboardingResponse,
    OrganizationSummaryResponse,
    OnboardingUserResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    require_platform_admin,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth")


def generate_temporary_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def queue_invite_email(email: str, username: str, temp_password: str) -> dict[str, str]:
    return {
        "status": "queued",
        "provider": "mock-email",
        "recipient": email,
        "message": f"Temporary password for {username} has been queued for delivery.",
        "temporary_password": temp_password,
    }


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register_user(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email.lower(),
        username=payload.username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        roles=payload.roles or ["REPORT_USER"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        roles=user.roles,
        full_name=user.full_name,
        organization_id=user.organization_id,
        force_password_reset=user.force_password_reset,
    )


@router.post("/admin/onboard-organization", status_code=status.HTTP_201_CREATED, response_model=OrganizationOnboardingResponse)
async def onboard_organization(
    payload: OrganizationOnboardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
) -> OrganizationOnboardingResponse:
    if db.query(Organization).filter(Organization.name == payload.organization_name.strip()).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organization already exists")

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

    created_users: list[OnboardingUserResponse] = []
    invited_users = [payload.organization_admin, *payload.users]
    for invited in invited_users:
        normalized_email = invited.email.lower()
        if db.query(User).filter(User.email == normalized_email).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User already exists: {normalized_email}")

        temp_password = generate_temporary_password()
        user = User(
            id=str(uuid.uuid4()),
            email=normalized_email,
            username=invited.username,
            full_name=invited.full_name,
            organization_id=org.id,
            password_hash=hash_password(temp_password),
            roles=[invited.role],
            force_password_reset=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        queue_invite_email(invited.email, invited.username, temp_password)
        created_users.append(
            OnboardingUserResponse(
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                role=user.roles[0],
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


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(user.email, {"user_id": user.id, "roles": user.roles})
    refresh_token = create_refresh_token(user.email, {"user_id": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        roles=current_user.roles,
        full_name=current_user.full_name,
        organization_id=current_user.organization_id,
        force_password_reset=current_user.force_password_reset,
    )


@router.post("/reset-password", response_model=UserResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    current_user.force_password_reset = False
    db.commit()
    db.refresh(current_user)
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        roles=current_user.roles,
        full_name=current_user.full_name,
        organization_id=current_user.organization_id,
        force_password_reset=current_user.force_password_reset,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest) -> TokenResponse:
    decoded = decode_token(payload.refresh_token)
    email = decoded.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing subject")

    access_token = create_access_token(email, {"user_id": decoded.get("user_id")})
    refresh_token = create_refresh_token(email, {"user_id": decoded.get("user_id")})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
