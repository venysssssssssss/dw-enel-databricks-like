"""Base classes and helpers for training predictive models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.common.logging import get_logger
from src.ml.contracts import TrainingResult
from src.ml.feature_store import FeatureStore
from src.ml.models.registry import LocalModelRegistry
from src.ml.models.tracking import start_tracking_run


@dataclass(slots=True)
class DatasetSplit:
    train: pd.DataFrame
    test: pd.DataFrame


class BaseModelTrainer:
    model_name: str = ""
    experiment_name: str = ""
    target_column: str = ""
    framework: str = "sklearn"
    threshold_map: dict[str, float] = {}

    def __init__(
        self,
        feature_store: FeatureStore,
        registry: LocalModelRegistry | None = None,
    ) -> None:
        self.feature_store = feature_store
        self.registry = registry or LocalModelRegistry()
        self.logger = get_logger(self.__class__.__name__)

    def load_training_data(self) -> pd.DataFrame:
        frame = self.feature_store.load_history(self.model_name)
        if frame.empty:
            raise ValueError(f"Feature set '{self.model_name}' ainda nao possui snapshots para treinamento.")
        frame["_observation_date"] = pd.to_datetime(frame["_observation_date"])
        return frame.sort_values("_observation_date")

    def temporal_split(self, frame: pd.DataFrame, test_date: date) -> DatasetSplit:
        split_ts = pd.Timestamp(test_date)
        train = frame.loc[frame["_observation_date"] < split_ts].copy()
        test = frame.loc[frame["_observation_date"] >= split_ts].copy()
        if train.empty or test.empty:
            raise ValueError("Split temporal invalido: treino ou teste ficou vazio.")
        return DatasetSplit(train=train, test=test)

    def feature_columns(self, frame: pd.DataFrame) -> list[str]:
        ignored = {self.target_column, "_observation_date"}
        return [column for column in frame.columns if column not in ignored and not column.startswith("target_")]

    def build_preprocessor(self, frame: pd.DataFrame, feature_columns: list[str]) -> ColumnTransformer:
        numeric_columns = [column for column in feature_columns if pd.api.types.is_numeric_dtype(frame[column])]
        categorical_columns = [column for column in feature_columns if column not in numeric_columns]
        return ColumnTransformer(
            transformers=[
                (
                    "numeric",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                        ]
                    ),
                    numeric_columns,
                ),
                (
                    "categorical",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="most_frequent")),
                            ("encoder", OneHotEncoder(handle_unknown="ignore")),
                        ]
                    ),
                    categorical_columns,
                ),
            ]
        )

    def evaluate_thresholds(self, metrics: dict[str, float]) -> dict[str, bool]:
        return {
            metric_name: float(metrics.get(metric_name, 0.0)) >= threshold
            for metric_name, threshold in self.threshold_map.items()
        }

    def register_bundle(
        self,
        *,
        model: Any,
        preprocessor: ColumnTransformer,
        feature_columns: list[str],
        metrics: dict[str, float],
        metadata: dict[str, Any] | None = None,
    ) -> TrainingResult:
        artifact = self.registry.register(
            self.model_name,
            bundle={
                "model": model,
                "preprocessor": preprocessor,
                "feature_columns": feature_columns,
                "target_column": self.target_column,
            },
            feature_columns=feature_columns,
            target_column=self.target_column,
            framework=self.framework,
            metrics=metrics,
            metadata=metadata,
        )
        return TrainingResult(
            model_name=self.model_name,
            version=artifact.version,
            artifact_path=artifact.artifact_path,
            framework=self.framework,
            metrics=metrics,
            train_rows=int(metadata.get("train_rows", 0) if metadata else 0),
            test_rows=int(metadata.get("test_rows", 0) if metadata else 0),
            feature_columns=tuple(feature_columns),
            threshold_results=self.evaluate_thresholds(metrics),
            metadata=metadata or {},
        )

    def start_run(self, suffix: str) -> Any:
        return start_tracking_run(self.experiment_name, f"{self.model_name}-{suffix}")
