from __future__ import annotations

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    code: str
    name: str
    price_monthly: float


class PlansResponse(BaseModel):
    plans: list[str]


class SubscriptionResponse(BaseModel):
    organization_id: str
    plan: str
    status: str = "active"


class UpgradeRequest(BaseModel):
    plan: str = Field(min_length=2, max_length=32)
