from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=150)
    full_name: str = Field(min_length=2, max_length=255)
    organization_id: str = Field(min_length=1, max_length=36)
    role: str = "REPORT_USER"


class UserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=150)
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    organization_id: str | None = Field(default=None, min_length=1, max_length=36)
    role: str | None = None
    status: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    organization_id: str
    role: str
    status: str
