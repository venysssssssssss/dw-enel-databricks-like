"""Shared typed contracts across ingestion, transformation and quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SourceType = Literal["csv", "database", "api", "excel"]
IngestionStrategy = Literal["incremental", "snapshot"]


class SourceDefinition(BaseModel):
    name: str
    type: SourceType
    path: str | None = None
    encoding: str = "utf-8"
    delimiter: str = ";"
    has_header: bool = True
    date_format: str | None = None


class ColumnDefinition(BaseModel):
    name: str
    source_name: str | None = None
    type: str
    nullable: bool = True
    description: str | None = None
    allowed_values: list[str] = Field(default_factory=list)
    format: str | None = None

    @property
    def input_name(self) -> str:
        return self.source_name or self.name


class QualityThresholds(BaseModel):
    min_rows: int = 0
    max_null_pct: float = 1.0
    critical_columns: list[str] = Field(default_factory=list)

    @field_validator("max_null_pct")
    @classmethod
    def validate_percentage(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("max_null_pct deve estar entre 0 e 1.")
        return value


class IngestionDefinition(BaseModel):
    strategy: IngestionStrategy
    watermark_column: str | None = None
    partition_by: str | None = None
    dedup_key: list[str] = Field(default_factory=list)
    dedup_order: str | None = None


class SourceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: SourceDefinition
    columns: list[ColumnDefinition] = Field(alias="schema")
    ingestion: IngestionDefinition
    quality: QualityThresholds = Field(default_factory=QualityThresholds)

    def schema_columns(self) -> list[str]:
        return [column.name for column in self.columns]

    def required_columns(self) -> list[str]:
        return [column.name for column in self.columns if not column.nullable]


@dataclass(frozen=True, slots=True)
class IODescriptor:
    name: str
    location: str
    rows: int | None = None
    format: str | None = None


@dataclass(frozen=True, slots=True)
class RejectStats:
    count: int = 0
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_id: str
    pipeline_name: str
    source_name: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    status: Literal["SUCCESS", "FAILURE", "WARNING"]
    inputs: tuple[IODescriptor, ...]
    outputs: tuple[IODescriptor, ...]
    rejects: RejectStats = field(default_factory=RejectStats)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReconciliationWindow:
    run_date: date
    layer_pair: Literal["bronze_to_silver", "silver_to_gold"]
    table_name: str
    threshold_pct: float


def resolve_project_path(project_root: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return project_root / candidate
