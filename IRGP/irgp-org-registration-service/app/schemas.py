from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    contact_email: EmailStr
    region: str = Field(min_length=2, max_length=100)
    plan: str = "free"


class OrganizationResponse(BaseModel):
    id: str
    name: str
    contact_email: str
    region: str
    plan: str
    status: str


class OrganizationUserInvitation(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=150)
    full_name: str | None = None
    role: str = "REPORT_USER"


class OrganizationOnboardRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=255)
    contact_email: EmailStr
    region: str = Field(min_length=2, max_length=100)
    plan: str = "starter"
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
