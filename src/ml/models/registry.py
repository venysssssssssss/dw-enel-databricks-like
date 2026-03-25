"""Local filesystem model registry with optional MLflow-compatible semantics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from src.common.config import get_settings
from src.ml.contracts import ModelArtifact


class LocalModelRegistry:
    """Persists model bundles on the local filesystem."""

    def __init__(self, root_path: Path | None = None) -> None:
        settings = get_settings()
        self.root_path = root_path or settings.model_registry_path
        self.root_path.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        model_name: str,
        *,
        bundle: dict[str, Any],
        feature_columns: list[str],
        target_column: str | None,
        framework: str,
        metrics: dict[str, float],
        metadata: dict[str, Any] | None = None,
    ) -> ModelArtifact:
        version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        model_dir = self.root_path / model_name / version
        model_dir.mkdir(parents=True, exist_ok=True)

        artifact_path = model_dir / "model.joblib"
        manifest_path = model_dir / "manifest.json"
        joblib.dump(bundle, artifact_path)
        manifest_payload = {
            "model_name": model_name,
            "artifact_path": str(artifact_path),
            "feature_columns": feature_columns,
            "target_column": target_column,
            "version": version,
            "framework": framework,
            "metrics": metrics,
            "metadata": metadata or {},
        }
        manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=True, default=str), encoding="utf-8")
        latest_path = self.root_path / model_name / "latest.joblib"
        latest_manifest = self.root_path / model_name / "latest.json"
        latest_path.write_bytes(artifact_path.read_bytes())
        latest_manifest.write_text(json.dumps(manifest_payload, ensure_ascii=True, default=str), encoding="utf-8")
        return ModelArtifact(
            model_name=model_name,
            artifact_path=artifact_path,
            feature_columns=tuple(feature_columns),
            target_column=target_column,
            version=version,
            framework=framework,
            metrics=metrics,
            metadata=metadata or {},
        )

    def load_bundle(self, model_name: str, version: str | None = None) -> dict[str, Any]:
        model_dir = self.root_path / model_name
        artifact_path = model_dir / "latest.joblib" if version is None else model_dir / version / "model.joblib"
        return joblib.load(artifact_path)

    def latest_artifact(self, model_name: str) -> ModelArtifact:
        manifest_path = self.root_path / model_name / "latest.json"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return ModelArtifact(
            model_name=payload["model_name"],
            artifact_path=Path(payload["artifact_path"]),
            feature_columns=tuple(payload["feature_columns"]),
            target_column=payload.get("target_column"),
            version=payload["version"],
            framework=payload["framework"],
            metrics={key: float(value) for key, value in payload["metrics"].items()},
            metadata=payload.get("metadata", {}),
        )
