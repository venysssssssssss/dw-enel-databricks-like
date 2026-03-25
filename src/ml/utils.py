"""Shared helpers for ML feature engineering and scoring."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd


def ensure_datetime_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    copy = frame.copy()
    for column in columns:
        if column in copy.columns:
            copy[column] = pd.to_datetime(copy[column], errors="coerce")
    return copy


def normalize_boolean(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().map({"true": True, "false": False}).fillna(False)


def coalesce_numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    copy = frame.copy()
    for column in columns:
        if column in copy.columns:
            copy[column] = pd.to_numeric(copy[column], errors="coerce").fillna(0.0)
    return copy


def observation_partition_path(base_path: Path, dataset: str, observation_date: date) -> Path:
    partition = f"observation_date={observation_date.isoformat()}"
    return base_path / dataset / partition
