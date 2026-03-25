"""Training pipeline for the delinquency-prediction model."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, recall_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit

from src.ml.contracts import TrainingResult
from src.common.config import get_settings
from src.ml.feature_store import FeatureStore
from src.ml.models.base import BaseModelTrainer

try:  # pragma: no cover
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None


class InadimplenciaModelTrainer(BaseModelTrainer):
    model_name = "inadimplencia"
    experiment_name = "enel-inadimplencia"
    target_column = "flag_inadimplente"
    threshold_map = {"auc_roc": 0.78}

    def __init__(self, feature_store: FeatureStore) -> None:
        super().__init__(feature_store)
        self.framework = "xgboost" if self._use_native_boosters() and XGBClassifier is not None else "sklearn"

    def train(self, test_date: date) -> TrainingResult:
        frame = self.load_training_data()
        split = self.temporal_split(frame, test_date)
        feature_columns = self.feature_columns(frame)
        preprocessor = self.build_preprocessor(frame, feature_columns)
        X_train = preprocessor.fit_transform(split.train[feature_columns])
        X_test = preprocessor.transform(split.test[feature_columns])
        y_train = split.train[self.target_column].astype(int)
        y_test = split.test[self.target_column].astype(int)

        base_model = self._build_model()
        calibrated = CalibratedClassifierCV(base_model, method="isotonic", cv=3)
        with self.start_run(test_date.isoformat()) as run:
            calibrated.fit(X_train, y_train)
            probabilities = calibrated.predict_proba(X_test)[:, 1]
            predictions = (probabilities >= 0.5).astype(int)
            metrics = {
                "auc_roc": float(roc_auc_score(y_test, probabilities)),
                "brier_score": float(brier_score_loss(y_test, probabilities)),
                "recall_top_20pct": float(self._recall_at_top_k(y_test, probabilities, 0.2)),
                "recall_binary": float(recall_score(y_test, predictions, zero_division=0)),
            }
            run.log_metrics(metrics)
        return self.register_bundle(
            model=calibrated,
            preprocessor=preprocessor,
            feature_columns=feature_columns,
            metrics=metrics,
            metadata={"train_rows": len(split.train), "test_rows": len(split.test)},
        )

    def cross_validate_temporal(self, test_date: date, n_splits: int = 5) -> pd.DataFrame:
        frame = self.load_training_data()
        frame = frame.loc[frame["_observation_date"] < pd.Timestamp(test_date)].copy()
        feature_columns = self.feature_columns(frame)
        preprocessor = self.build_preprocessor(frame, feature_columns)
        transformed = preprocessor.fit_transform(frame[feature_columns])
        target = frame[self.target_column].astype(int).to_numpy()

        scores: list[dict[str, float]] = []
        splitter = TimeSeriesSplit(n_splits=n_splits)
        for fold, (train_index, test_index) in enumerate(splitter.split(transformed), start=1):
            calibrated = CalibratedClassifierCV(self._build_model(), method="sigmoid", cv=3)
            calibrated.fit(transformed[train_index], target[train_index])
            probabilities = calibrated.predict_proba(transformed[test_index])[:, 1]
            scores.append(
                {
                    "fold": float(fold),
                    "auc_roc": float(roc_auc_score(target[test_index], probabilities)),
                    "brier_score": float(brier_score_loss(target[test_index], probabilities)),
                }
            )
        return pd.DataFrame(scores)

    def _build_model(self) -> object:
        if self._use_native_boosters() and XGBClassifier is not None:
            return XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric="logloss",
            )
        return RandomForestClassifier(n_estimators=250, max_depth=8, class_weight="balanced", random_state=42)

    def _use_native_boosters(self) -> bool:
        return bool(get_settings().ml_use_native_boosters)

    def _recall_at_top_k(self, y_true: pd.Series, probabilities: np.ndarray, k_ratio: float) -> float:
        top_k = max(1, int(len(probabilities) * k_ratio))
        top_indices = np.argsort(probabilities)[-top_k:]
        selected = y_true.to_numpy()[top_indices]
        positives = max(1, int(y_true.sum()))
        return float(selected.sum() / positives)
