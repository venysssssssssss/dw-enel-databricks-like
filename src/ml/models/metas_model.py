"""Training pipeline for goal-projection models."""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, mean_absolute_error, mean_squared_error

from src.ml.contracts import TrainingResult
from src.ml.feature_store import FeatureStore
from src.ml.models.base import BaseModelTrainer


class MetasModelTrainer(BaseModelTrainer):
    model_name = "metas"
    experiment_name = "enel-metas"
    target_column = "target_pct_atingimento"
    framework = "sklearn"
    threshold_map = {"accuracy_flag_risco": 0.70}

    def __init__(self, feature_store: FeatureStore) -> None:
        super().__init__(feature_store)

    def train(self, test_date: date) -> TrainingResult:
        frame = self.load_training_data()
        split = self.temporal_split(frame, test_date)
        feature_columns = self.feature_columns(frame)
        preprocessor = self.build_preprocessor(frame, feature_columns)
        X_train = preprocessor.fit_transform(split.train[feature_columns])
        X_test = preprocessor.transform(split.test[feature_columns])
        y_train = split.train[self.target_column].astype(float)
        y_test = split.test[self.target_column].astype(float)
        y_train_flag = split.train["target_flag_risco"].astype(int)
        y_test_flag = split.test["target_flag_risco"].astype(int)

        regressor = HistGradientBoostingRegressor(learning_rate=0.05, max_depth=6, max_iter=300)
        classifier = LogisticRegression(max_iter=500)
        with self.start_run(test_date.isoformat()) as run:
            regressor.fit(X_train, y_train)
            classifier.fit(X_train, y_train_flag)
            reg_predictions = regressor.predict(X_test)
            clf_predictions = classifier.predict_proba(X_test)[:, 1]
            ensemble_prediction = (0.6 * reg_predictions) + (0.4 * (100.0 * (1.0 - clf_predictions)))
            risk_flag_prediction = (clf_predictions >= 0.5).astype(int)
            metrics = {
                "rmse": float(np.sqrt(mean_squared_error(y_test, ensemble_prediction))),
                "mae": float(mean_absolute_error(y_test, ensemble_prediction)),
                "accuracy_flag_risco": float(accuracy_score(y_test_flag, risk_flag_prediction)),
            }
            run.log_metrics(metrics)
        return self.register_bundle(
            model={"regressor": regressor, "classifier": classifier},
            preprocessor=preprocessor,
            feature_columns=feature_columns,
            metrics=metrics,
            metadata={"train_rows": len(split.train), "test_rows": len(split.test)},
        )

    def explain_prediction(self, bundle: dict[str, Any], row: pd.DataFrame) -> dict[str, object]:
        preprocessor = bundle["preprocessor"]
        models = bundle["model"]
        transformed = preprocessor.transform(row)
        projecao = float(
            (0.6 * models["regressor"].predict(transformed)[0])
            + (0.4 * (100.0 * (1.0 - models["classifier"].predict_proba(transformed)[:, 1][0])))
        )
        top_features = self._top_feature_impacts(bundle["feature_columns"], row.iloc[0])
        return {
            "projecao_pct": round(projecao, 1),
            "status": "EM_RISCO" if projecao < 90.0 else "NO_CAMINHO",
            "explicacao": [
                f"{name}: {'ALTO' if impact >= 0 else 'BAIXO'} ({abs(impact):.1f})"
                for name, impact in top_features
            ],
        }

    def _top_feature_impacts(self, feature_columns: list[str], row: pd.Series, limit: int = 3) -> list[tuple[str, float]]:
        impacts = []
        for column in feature_columns:
            value = row[column]
            numeric_value = float(value) if isinstance(value, (int, float, np.integer, np.floating)) else 0.0
            impacts.append((column, numeric_value))
        impacts.sort(key=lambda item: abs(item[1]), reverse=True)
        return impacts[:limit]
