"""Training pipeline for the delay-prediction model."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import Pipeline

from src.ml.contracts import TrainingResult
from src.common.config import get_settings
from src.ml.feature_store import FeatureStore
from src.ml.models.base import BaseModelTrainer

try:  # pragma: no cover
    from lightgbm import LGBMClassifier
except ImportError:  # pragma: no cover
    LGBMClassifier = None


class AtrasoModelTrainer(BaseModelTrainer):
    model_name = "atraso_entrega"
    experiment_name = "enel-atraso-entrega"
    target_column = "target_flag_atraso"
    threshold_map = {"auc_roc": 0.75, "recall_atraso": 0.70, "f1_atraso": 0.58}

    def __init__(self, feature_store: FeatureStore) -> None:
        super().__init__(feature_store)
        self.framework = "lightgbm" if self._use_native_boosters() and LGBMClassifier is not None else "sklearn"

    def train(self, test_date: date) -> TrainingResult:
        frame = self.load_training_data()
        split = self.temporal_split(frame, test_date)
        feature_columns = self.feature_columns(frame)
        preprocessor = self.build_preprocessor(frame, feature_columns)

        X_train = preprocessor.fit_transform(split.train[feature_columns])
        X_test = preprocessor.transform(split.test[feature_columns])
        y_train = split.train[self.target_column].astype(int)
        y_test = split.test[self.target_column].astype(int)

        model = self._build_model()
        with self.start_run(test_date.isoformat()) as run:
            run.log_params({"framework": self.framework, "test_date": test_date.isoformat()})
            model.fit(X_train, y_train)
            probabilities = self._predict_proba(model, X_test)
            predictions = (probabilities >= 0.5).astype(int)
            metrics = {
                "auc_roc": float(roc_auc_score(y_test, probabilities)),
                "recall_atraso": float(recall_score(y_test, predictions, zero_division=0)),
                "precision_atraso": float(precision_score(y_test, predictions, zero_division=0)),
                "f1_atraso": float(f1_score(y_test, predictions, zero_division=0)),
                "accuracy": float(accuracy_score(y_test, predictions)),
                "train_positive_rate": float(y_train.mean()),
                "test_positive_rate": float(y_test.mean()),
            }
            run.log_metrics(metrics)
        return self.register_bundle(
            model=model,
            preprocessor=preprocessor,
            feature_columns=feature_columns,
            metrics=metrics,
            metadata={"train_rows": len(split.train), "test_rows": len(split.test)},
        )

    def _build_model(self) -> object:
        if self._use_native_boosters() and LGBMClassifier is not None:
            return LGBMClassifier(
                objective="binary",
                n_estimators=200,
                learning_rate=0.05,
                num_leaves=31,
                max_depth=8,
                subsample=0.8,
                colsample_bytree=0.8,
            )
        return HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_depth=8,
            max_iter=200,
        )

    def _use_native_boosters(self) -> bool:
        return bool(get_settings().ml_use_native_boosters)

    def _predict_proba(self, model: object, transformed: object) -> np.ndarray:
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(transformed)
            if probabilities.ndim == 2:
                return probabilities[:, 1]
        return pd.Series(model.predict(transformed)).astype(float).clip(lower=0.0, upper=1.0).to_numpy()
