"""Feature and prediction drift monitoring utilities."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.config import get_settings
from src.common.logging import get_logger
from src.ml.contracts import DriftResult
from src.ml.feature_store import FeatureStore


class DriftDetector:
    """Calculates PSI-based drift over feature snapshots."""

    def __init__(
        self,
        model_name: str,
        feature_store: FeatureStore,
        monitoring_root: Path | None = None,
    ) -> None:
        settings = get_settings()
        self.model_name = model_name
        self.feature_store = feature_store
        self.monitoring_root = monitoring_root or settings.monitoring_path
        self.monitoring_root.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(self.__class__.__name__)

    def check_feature_drift(self, reference_date: date, current_date: date) -> list[DriftResult]:
        reference = self.feature_store.load(self.model_name, reference_date)
        current = self.feature_store.load(self.model_name, current_date)
        numeric_columns = [
            column
            for column in reference.columns
            if column in current.columns
            and column not in {"_observation_date"}
            and pd.api.types.is_numeric_dtype(reference[column])
        ]
        results = []
        for column in numeric_columns:
            psi = self._calculate_psi(reference[column], current[column])
            results.append(
                DriftResult(
                    feature_name=column,
                    drift_score=psi,
                    status=self._classify_psi(psi),
                    reference_date=reference_date,
                    current_date=current_date,
                )
            )
        return results

    def save_report(self, reference_date: date, current_date: date) -> Path:
        results = self.check_feature_drift(reference_date, current_date)
        report = pd.DataFrame(
            {
                "feature_name": [result.feature_name for result in results],
                "drift_score": [result.drift_score for result in results],
                "status": [result.status for result in results],
                "reference_date": [result.reference_date.isoformat() for result in results],
                "current_date": [result.current_date.isoformat() for result in results],
            }
        )
        output_path = self.monitoring_root / self.model_name / f"drift_{reference_date}_{current_date}.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output_path, index=False)
        return output_path

    def _calculate_psi(self, reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
        ref = pd.to_numeric(reference, errors="coerce").fillna(0.0).to_numpy()
        cur = pd.to_numeric(current, errors="coerce").fillna(0.0).to_numpy()
        if np.allclose(ref, ref[0]) and np.allclose(cur, cur[0]):
            return 0.0
        quantiles = np.unique(np.quantile(ref, np.linspace(0.0, 1.0, bins + 1)))
        if len(quantiles) <= 2:
            return 0.0
        ref_bins = np.histogram(ref, bins=quantiles)[0] / max(len(ref), 1)
        cur_bins = np.histogram(cur, bins=quantiles)[0] / max(len(cur), 1)
        ref_bins = np.clip(ref_bins, 1e-6, None)
        cur_bins = np.clip(cur_bins, 1e-6, None)
        return float(np.sum((cur_bins - ref_bins) * np.log(cur_bins / ref_bins)))

    def _classify_psi(self, psi: float) -> str:
        if psi < 0.1:
            return "STABLE"
        if psi < 0.25:
            return "WARNING"
        return "CRITICAL"
