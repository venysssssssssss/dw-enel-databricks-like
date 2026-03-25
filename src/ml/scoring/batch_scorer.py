"""Batch scoring for registered ML models."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from src.common.config import get_settings
from src.common.logging import get_logger
from src.ml.contracts import ScoringResult
from src.ml.feature_store import FeatureStore
from src.ml.models.registry import LocalModelRegistry


class BatchScorer:
    """Loads a registered model, scores a feature snapshot and persists the result."""

    output_prefix = "score"

    def __init__(
        self,
        model_name: str,
        feature_store: FeatureStore,
        registry: LocalModelRegistry | None = None,
        scores_root: Path | None = None,
    ) -> None:
        settings = get_settings()
        self.model_name = model_name
        self.feature_store = feature_store
        self.registry = registry or LocalModelRegistry()
        self.scores_root = scores_root or settings.scores_path
        self.scores_root.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(self.__class__.__name__)

    def score(self, scoring_date: date) -> ScoringResult:
        start_time = datetime.now(timezone.utc)
        run_id = str(uuid4())
        feature_frame = self.feature_store.load(self.model_name, scoring_date)
        bundle = self.registry.load_bundle(self.model_name)
        preprocessor = bundle["preprocessor"]
        model = bundle["model"]
        feature_columns = bundle["feature_columns"]

        transformed = preprocessor.transform(feature_frame[feature_columns])
        score_frame = self._build_score_frame(feature_frame, model, transformed, feature_columns)
        self._validate_scores(score_frame)
        output_path = self._publish_scores(score_frame, scoring_date)
        duration_seconds = (datetime.now(timezone.utc) - start_time).total_seconds()
        artifact = self.registry.latest_artifact(self.model_name)
        return ScoringResult(
            run_id=run_id,
            model_name=self.model_name,
            model_version=artifact.version,
            rows_scored=len(score_frame),
            scoring_date=scoring_date,
            duration_seconds=duration_seconds,
            output_path=output_path,
            metrics={"mean_score": float(score_frame["score"].mean())},
        )

    def _build_score_frame(
        self,
        feature_frame: pd.DataFrame,
        model: object,
        transformed: object,
        feature_columns: list[str],
    ) -> pd.DataFrame:
        probabilities = self._predict(model, transformed)
        explanations = self._build_explanations(feature_frame, feature_columns)
        return pd.DataFrame(
            {
                "entity_id": feature_frame.iloc[:, 0].astype(str),
                "score": probabilities,
                "explanations": explanations,
                "data_scoring": feature_frame["_observation_date"],
            }
        )

    def _predict(self, model: object, transformed: object) -> np.ndarray:
        if isinstance(model, dict):
            regressor = model["regressor"]
            classifier = model["classifier"]
            regression = regressor.predict(transformed)
            classification = classifier.predict_proba(transformed)[:, 1]
            return np.clip((0.6 * (regression / 100.0)) + (0.4 * classification), 0.0, 1.0)
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(transformed)
            if probabilities.ndim == 2:
                return probabilities[:, 1]
        if hasattr(model, "decision_function"):
            scores = model.decision_function(transformed)
            normalized = (scores - scores.min()) / (scores.max() - scores.min() or 1.0)
            return normalized
        predictions = model.predict(transformed)
        return np.clip(np.asarray(predictions, dtype=float), 0.0, 1.0)

    def _build_explanations(self, feature_frame: pd.DataFrame, feature_columns: list[str]) -> list[str]:
        explanations: list[str] = []
        for _, row in feature_frame[feature_columns].iterrows():
            numeric_candidates = []
            for column in feature_columns:
                value = row[column]
                if isinstance(value, (int, float, np.integer, np.floating)):
                    numeric_candidates.append((column, float(value)))
            numeric_candidates.sort(key=lambda item: abs(item[1]), reverse=True)
            payload = [
                {
                    "feature_name": column,
                    "shap_value": value,
                    "direction": "AUMENTA_RISCO" if value >= 0 else "DIMINUI_RISCO",
                }
                for column, value in numeric_candidates[:3]
            ]
            explanations.append(json.dumps(payload, ensure_ascii=True))
        return explanations

    def _validate_scores(self, score_frame: pd.DataFrame) -> None:
        if score_frame["score"].isna().any():
            raise ValueError("Scores com valores nulos.")
        if not score_frame["score"].between(0.0, 1.0).all():
            raise ValueError("Scores fora do intervalo 0-1.")

    def _publish_scores(self, score_frame: pd.DataFrame, scoring_date: date) -> Path:
        output_dir = self.scores_root / self.output_prefix / f"data_scoring={scoring_date.isoformat()}"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "scores.csv"
        score_frame.to_csv(output_path, index=False)
        return output_path


class AtrasoScorer(BatchScorer):
    output_prefix = "score_atraso_entrega"


class InadimplenciaScorer(BatchScorer):
    output_prefix = "score_inadimplencia"


class MetasScorer(BatchScorer):
    output_prefix = "score_metas"


class AnomaliaScorer(BatchScorer):
    output_prefix = "score_anomalias"
