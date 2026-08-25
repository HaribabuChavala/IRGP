from __future__ import annotations

from pydantic import BaseModel, Field


class DataSourceCreateRequest(BaseModel):
    organization_id: str = Field(min_length=1, max_length=36)
    name: str = Field(min_length=2, max_length=255)
    type: str = Field(default="postgres", min_length=2, max_length=64)
    connection_string: str = Field(min_length=10, max_length=2000)


class DataSourceResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    type: str
    connection_string: str
    status: str


class DataSourceListResponse(BaseModel):
    data_sources: list[DataSourceResponse]
