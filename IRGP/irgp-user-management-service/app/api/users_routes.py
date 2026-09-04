from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import UserCreateRequest, UserResponse, UserUpdateRequest
from app.security import require_platform_admin

router = APIRouter(prefix="/api/v1/admin/users", tags=["user-management"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
) -> User:
    normalized_email = payload.email.lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing:
        raise HTTPException(status_code=409, detail="User email already exists")

    user = User(
        id=str(uuid.uuid4()),
        email=normalized_email,
        username=payload.username,
        full_name=payload.full_name,
        organization_id=payload.organization_id,
        role=payload.role,
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
    q: str | None = Query(default=None, alias="query"),
) -> list[User]:
    stmt = select(User)
    if q:
        stmt = stmt.where((User.email.ilike(f"%{q}%")) | (User.username.ilike(f"%{q}%")))
    return list(db.scalars(stmt.order_by(User.created_at.desc())).all())


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[dict, Depends(require_platform_admin)],
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.username is not None:
        user.username = payload.username
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.organization_id is not None:
        user.organization_id = payload.organization_id
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        user.status = payload.status

    db.commit()
    db.refresh(user)
    return user
