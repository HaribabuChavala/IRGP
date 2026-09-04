from __future__ import annotations

from pydantic import BaseModel, Field


class ReminderCreateRequest(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=2, max_length=255)
    schedule: str = Field(min_length=2, max_length=128)
    message: str = Field(min_length=1, max_length=1000)


class ReminderResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    schedule: str
    message: str
    status: str


class ReminderListResponse(BaseModel):
    reminders: list[ReminderResponse]
