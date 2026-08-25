from __future__ import annotations

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=2, max_length=255)
    data_source_id: str = Field(min_length=1, max_length=36)
    template: str = Field(default="default", min_length=1, max_length=64)


class ReportJobResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    data_source_id: str
    template: str
    status: str


class ReportResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    data_source_id: str
    job_id: str
    status: str
