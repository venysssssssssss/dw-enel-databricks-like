"""Minimal MLflow model registry client abstraction."""

from __future__ import annotations

from pathlib import Path


class LocalModelRegistryClient:
    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path

    def latest_model_path(self, model_name: str) -> Path:
        return self.registry_path / model_name / "latest.joblib"
