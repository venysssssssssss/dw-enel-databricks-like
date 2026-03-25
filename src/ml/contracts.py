"""Typed ML contracts for features, training, scoring and monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class FeatureSetManifest:
    feature_set: str
    observation_date: date
    rows: int
    columns: tuple[str, ...]
    entity_key: str
    target_columns: tuple[str, ...] = ()
    source_files: tuple[str, ...] = ()
    null_counts: dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelArtifact:
    model_name: str
    artifact_path: Path
    feature_columns: tuple[str, ...]
    target_column: str | None
    version: str
    framework: str
    metrics: dict[str, float]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TrainingResult:
    model_name: str
    version: str
    artifact_path: Path
    framework: str
    metrics: dict[str, float]
    train_rows: int
    test_rows: int
    feature_columns: tuple[str, ...]
    threshold_results: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScoringResult:
    run_id: str
    model_name: str
    model_version: str
    rows_scored: int
    scoring_date: date
    duration_seconds: float
    output_path: Path
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DriftResult:
    feature_name: str
    drift_score: float
    status: Literal["STABLE", "WARNING", "CRITICAL"]
    reference_date: date
    current_date: date
    details: dict[str, Any] = field(default_factory=dict)
