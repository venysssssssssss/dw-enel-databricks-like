"""Materialized local feature store used by the ML pipelines."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from src.common.config import get_settings
from src.ml.contracts import FeatureSetManifest
from src.ml.utils import observation_partition_path


class FeatureStore:
    """Persists and loads feature snapshots partitioned by observation date."""

    def __init__(self, root_path: Path | None = None) -> None:
        settings = get_settings()
        self.root_path = root_path or settings.feature_store_path
        self.root_path.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        feature_set: str,
        observation_date: date,
        frame: pd.DataFrame,
        *,
        entity_key: str,
        target_columns: list[str] | None = None,
        source_files: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FeatureSetManifest:
        partition_path = observation_partition_path(self.root_path, feature_set, observation_date)
        partition_path.mkdir(parents=True, exist_ok=True)

        dataset_path = partition_path / "dataset.csv"
        manifest_path = partition_path / "manifest.json"
        frame.to_csv(dataset_path, index=False)

        manifest = FeatureSetManifest(
            feature_set=feature_set,
            observation_date=observation_date,
            rows=len(frame),
            columns=tuple(frame.columns.tolist()),
            entity_key=entity_key,
            target_columns=tuple(target_columns or []),
            source_files=tuple(source_files or []),
            null_counts={column: int(frame[column].isna().sum()) for column in frame.columns},
            metadata=metadata or {},
        )
        manifest_path.write_text(json.dumps(asdict(manifest), ensure_ascii=True, default=str), encoding="utf-8")
        return manifest

    def load(self, feature_set: str, observation_date: date) -> pd.DataFrame:
        dataset_path = observation_partition_path(self.root_path, feature_set, observation_date) / "dataset.csv"
        return pd.read_csv(dataset_path)

    def load_manifest(self, feature_set: str, observation_date: date) -> FeatureSetManifest:
        manifest_path = observation_partition_path(self.root_path, feature_set, observation_date) / "manifest.json"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return FeatureSetManifest(
            feature_set=payload["feature_set"],
            observation_date=date.fromisoformat(payload["observation_date"]),
            rows=int(payload["rows"]),
            columns=tuple(payload["columns"]),
            entity_key=payload["entity_key"],
            target_columns=tuple(payload.get("target_columns", [])),
            source_files=tuple(payload.get("source_files", [])),
            null_counts={key: int(value) for key, value in payload.get("null_counts", {}).items()},
            metadata=payload.get("metadata", {}),
        )

    def load_history(self, feature_set: str) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for dataset_path in sorted(self.root_path.glob(f"{feature_set}/observation_date=*/dataset.csv")):
            frame = pd.read_csv(dataset_path)
            observation_token = dataset_path.parent.name.split("=", maxsplit=1)[1]
            frame["_observation_date"] = observation_token
            frames.append(frame)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def latest_snapshot(self, feature_set: str) -> tuple[date, pd.DataFrame]:
        dates = self.available_dates(feature_set)
        if not dates:
            raise FileNotFoundError(f"Feature set '{feature_set}' ainda não foi materializado.")
        latest_date = dates[-1]
        return latest_date, self.load(feature_set, latest_date)

    def available_dates(self, feature_set: str) -> list[date]:
        dates = []
        for partition_path in sorted((self.root_path / feature_set).glob("observation_date=*")):
            dates.append(date.fromisoformat(partition_path.name.split("=", maxsplit=1)[1]))
        return dates
