"""Experiment tracking helpers with optional MLflow support."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.common.config import get_settings
from src.common.logging import get_logger

try:  # pragma: no cover
    import mlflow
except ImportError:  # pragma: no cover
    mlflow = None


logger = get_logger(__name__)


@dataclass(slots=True)
class TrackingRun(AbstractContextManager["TrackingRun"]):
    experiment_name: str
    run_name: str
    uri: str
    enabled: bool
    params: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
    _mlflow_run: Any | None = None

    def __enter__(self) -> "TrackingRun":
        if self.enabled and mlflow is not None:
            mlflow.set_tracking_uri(self.uri)
            mlflow.set_experiment(self.experiment_name)
            self._mlflow_run = mlflow.start_run(run_name=self.run_name)
            self.run_id = str(self._mlflow_run.info.run_id)
        return self

    def log_params(self, params: dict[str, Any]) -> None:
        self.params.update(params)
        if self.enabled and mlflow is not None:
            mlflow.log_params(params)

    def log_metrics(self, metrics: dict[str, float]) -> None:
        self.metrics.update(metrics)
        if self.enabled and mlflow is not None:
            mlflow.log_metrics(metrics)

    def log_artifact(self, local_path: str, artifact_path: str) -> None:
        self.artifacts[artifact_path] = local_path
        if self.enabled and mlflow is not None:
            mlflow.log_artifact(local_path, artifact_path)

    def __exit__(self, exc_type: Any, exc: Any, exc_tb: Any) -> None:
        if self.enabled and mlflow is not None and self._mlflow_run is not None:
            mlflow.end_run(status="FAILED" if exc is not None else "FINISHED")
        if exc is not None:
            logger.warning("tracking_run_failed", experiment=self.experiment_name, error=str(exc))
        return None


def start_tracking_run(experiment_name: str, run_name: str) -> TrackingRun:
    settings = get_settings()
    return TrackingRun(
        experiment_name=experiment_name,
        run_name=run_name,
        uri=settings.mlflow_tracking_uri,
        enabled=settings.mlflow_tracking_enabled,
    )
