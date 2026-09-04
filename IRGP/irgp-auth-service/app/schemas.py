from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8)
    roles: list[str] = Field(default_factory=list)
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ResetPasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    roles: list[str]
    full_name: str | None = None
    organization_id: str | None = None
    force_password_reset: bool = False


class OrganizationUserInvitation(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=150)
    full_name: str | None = None
    role: str = "REPORT_USER"


class OrganizationOnboardRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    contact_email: EmailStr
    region: str = Field(min_length=2, max_length=100)
    plan: str = Field(default="starter")
    organization_admin: OrganizationUserInvitation
    users: list[OrganizationUserInvitation] = Field(default_factory=list)


class OnboardingUserResponse(BaseModel):
    email: str
    username: str
    full_name: str | None = None
    role: str
    force_password_reset: bool
    temporary_password: str


class OrganizationSummaryResponse(BaseModel):
    id: str
    name: str
    contact_email: str
    region: str
    plan: str
    status: str


class OrganizationOnboardingResponse(BaseModel):
    organization: OrganizationSummaryResponse
    created_users: list[OnboardingUserResponse]
    email_delivery: str = "queued"
