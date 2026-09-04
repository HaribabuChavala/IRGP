from __future__ import annotations

from pydantic import BaseModel, Field


class DataSourceSummary(BaseModel):
    id: str
    name: str
    type: str
    status: str


class DashboardResponse(BaseModel):
    organization_id: str
    total_queries: int = Field(default=0)
    data_source_count: int = Field(default=0)
    recent_executions: int = Field(default=0)


class DataSourcesResponse(BaseModel):
    organization_id: str
    data_sources: list[DataSourceSummary] = Field(default_factory=list)
