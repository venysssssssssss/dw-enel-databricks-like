"""Shared API schemas."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class DateRangeFilter(BaseModel):
    periodo_inicio: date
    periodo_fim: date


class HierarchyFilter(BaseModel):
    distribuidora: int | None = None
    ut: int | None = None
    co: int | None = None
    base: int | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: list[T]
    total: int
    page: int
    page_size: int
