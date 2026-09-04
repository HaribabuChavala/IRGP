from __future__ import annotations

from pydantic import BaseModel, Field


class NotificationCreateRequest(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    message: str = Field(min_length=1, max_length=1000)
    type: str = "INFO"


class NotificationResponse(BaseModel):
    id: str
    organization_id: str
    message: str
    type: str
    read: bool


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
