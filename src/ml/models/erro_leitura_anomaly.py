"""Space-time anomaly detection for erro de leitura hotspots."""

from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest


class ErroLeituraAnomalyDetector:
    """Detects daily spikes by region and error class."""

    def detect(
        self,
        frame: pd.DataFrame,
        *,
        date_column: str = "dt_ingresso",
        region_column: str = "_source_region",
        class_column: str = "classe_erro",
    ) -> pd.DataFrame:
        required = {date_column, region_column, class_column}
        missing = sorted(required.difference(frame.columns))
        if missing:
            raise ValueError(f"Colunas obrigatorias ausentes para anomalias de erro leitura: {missing}")
        working = frame.copy()
        working[date_column] = pd.to_datetime(working[date_column], errors="coerce")
        working = working.dropna(subset=[date_column])
        working["data"] = working[date_column].dt.date
        aggregated = (
            working.groupby(["data", region_column, class_column], dropna=False)
            .size()
            .reset_index(name="qtd_erros")
            .sort_values(["data", region_column, class_column])
        )
        if aggregated.empty:
            return aggregated.assign(zscore=0.0, anomaly_score=0.0, is_anomaly=False)

        aggregated["rolling_mean_7d"] = aggregated.groupby([region_column, class_column])["qtd_erros"].transform(
            lambda values: values.rolling(7, min_periods=1).mean()
        )
        aggregated["rolling_std_7d"] = aggregated.groupby([region_column, class_column])["qtd_erros"].transform(
            lambda values: values.rolling(7, min_periods=1).std().fillna(0.0)
        )
        denominator = aggregated["rolling_std_7d"].replace({0.0: 1.0})
        aggregated["zscore"] = (aggregated["qtd_erros"] - aggregated["rolling_mean_7d"]) / denominator
        if len(aggregated) >= 4:
            model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
            features = aggregated[["qtd_erros", "rolling_mean_7d", "zscore"]].fillna(0.0)
            aggregated["anomaly_score"] = -model.fit(features).decision_function(features)
            aggregated["is_anomaly"] = (model.predict(features) == -1) | aggregated["zscore"].abs().ge(3.0)
        else:
            aggregated["anomaly_score"] = aggregated["zscore"].abs()
            aggregated["is_anomaly"] = aggregated["zscore"].abs().ge(3.0)
        return aggregated
