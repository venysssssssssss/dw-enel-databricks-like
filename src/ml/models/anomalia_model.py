"""Training pipeline for anomaly detection."""

from __future__ import annotations

from datetime import date

import pandas as pd
from sklearn.ensemble import IsolationForest

from src.ml.contracts import TrainingResult
from src.ml.feature_store import FeatureStore
from src.ml.models.base import BaseModelTrainer


class AnomaliaModelTrainer(BaseModelTrainer):
    model_name = "anomalias"
    experiment_name = "enel-anomalias"
    target_column = ""
    framework = "sklearn"
    threshold_map: dict[str, float] = {}

    def __init__(self, feature_store: FeatureStore) -> None:
        super().__init__(feature_store)

    def feature_columns(self, frame: pd.DataFrame) -> list[str]:
        return [column for column in frame.columns if column not in {"entidade_id", "_observation_date"}]

    def train(self, test_date: date) -> TrainingResult:
        frame = self.load_training_data()
        split = self.temporal_split(frame, test_date)
        feature_columns = self.feature_columns(frame)
        preprocessor = self.build_preprocessor(frame, feature_columns)
        X_train = preprocessor.fit_transform(split.train[feature_columns])
        model = IsolationForest(n_estimators=200, contamination=0.1, random_state=42)
        with self.start_run(test_date.isoformat()) as run:
            model.fit(X_train)
            test_scores = -model.decision_function(preprocessor.transform(split.test[feature_columns]))
            metrics = {
                "score_mean": float(test_scores.mean()),
                "score_std": float(test_scores.std()),
            }
            run.log_metrics(metrics)
        return self.register_bundle(
            model=model,
            preprocessor=preprocessor,
            feature_columns=feature_columns,
            metrics=metrics,
            metadata={"train_rows": len(split.train), "test_rows": len(split.test)},
        )
