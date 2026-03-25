"""Feature engineering for anomaly detection."""

from __future__ import annotations

import pandas as pd

from src.ml.features.base import BaseFeatureBuilder
from src.ml.utils import coalesce_numeric, ensure_datetime_columns


class AnomaliaFeatureBuilder(BaseFeatureBuilder):
    feature_set_name = "anomalias"
    entity_key = "entidade_id"
    target_columns: tuple[str, ...] = ()

    def build(self, notas: pd.DataFrame, pagamentos: pd.DataFrame | None = None) -> pd.DataFrame:
        self.validate_columns(notas, ["cod_base", "data_criacao", "status"])
        frame = ensure_datetime_columns(notas, ["data_criacao"])
        frame = frame.loc[frame["data_criacao"].dt.date <= self.observation_date].copy()
        if frame.empty:
            return pd.DataFrame(columns=["entidade_id", "_observation_date"])

        aggregated = (
            frame.groupby("cod_base", dropna=False)
            .agg(
                total_notas=("status", "count"),
                taxa_devolucao=("status", lambda values: float(values.eq("DEVOLVIDA").mean())),
                taxa_cancelamento=("status", lambda values: float(values.eq("CANCELADA").mean())),
            )
            .reset_index()
            .rename(columns={"cod_base": "entidade_id"})
        )

        if pagamentos is not None and not pagamentos.empty:
            payment_frame = ensure_datetime_columns(pagamentos, ["data_vencimento", "data_pagamento"])
            payment_frame = payment_frame.loc[
                payment_frame["data_vencimento"].dt.date <= self.observation_date
            ].copy()
            payment_frame["flag_inadimplente"] = (
                payment_frame["data_pagamento"].isna()
                | (payment_frame["data_pagamento"] > payment_frame["data_vencimento"])
            ).astype(int)
            if "cod_base" in payment_frame.columns:
                inadimplencia = (
                    payment_frame.groupby("cod_base", dropna=False)
                    .agg(taxa_inadimplencia=("flag_inadimplente", "mean"))
                    .reset_index()
                    .rename(columns={"cod_base": "entidade_id"})
                )
                aggregated = aggregated.merge(inadimplencia, on="entidade_id", how="left")

        for column in [value for value in aggregated.columns if value != "entidade_id"]:
            aggregated[f"{column}_zscore"] = _zscore(aggregated[column])
        aggregated["_observation_date"] = self.observation_date.isoformat()
        return coalesce_numeric(aggregated, [column for column in aggregated.columns if column != "entidade_id"])


def _zscore(series: pd.Series) -> pd.Series:
    std = float(series.std(ddof=0))
    if std == 0.0:
        return pd.Series([0.0] * len(series), index=series.index)
    return (series - float(series.mean())) / std
