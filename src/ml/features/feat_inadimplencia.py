"""Feature engineering for delinquency prediction."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from src.ml.features.base import BaseFeatureBuilder
from src.ml.utils import coalesce_numeric, ensure_datetime_columns


class InadimplenciaFeatureBuilder(BaseFeatureBuilder):
    feature_set_name = "inadimplencia"
    entity_key = "cod_fatura"
    target_columns = ("flag_inadimplente",)

    def build(self, pagamentos: pd.DataFrame, cadastro_ucs: pd.DataFrame | None = None) -> pd.DataFrame:
        self.validate_columns(
            pagamentos,
            ["cod_fatura", "cod_uc", "valor_fatura", "data_vencimento", "data_pagamento"],
        )
        frame = ensure_datetime_columns(pagamentos, ["data_vencimento", "data_pagamento"])
        frame = coalesce_numeric(frame, ["valor_fatura", "valor_pago"])
        frame = frame.loc[frame["data_vencimento"].dt.date <= self.observation_date].copy()
        if frame.empty:
            return pd.DataFrame(columns=["cod_fatura", "_observation_date", *self.target_columns])

        frame["dias_atraso_pagamento"] = (
            frame["data_pagamento"].fillna(pd.Timestamp(self.observation_date)).dt.normalize()
            - frame["data_vencimento"].dt.normalize()
        ).dt.days.clip(lower=0)
        frame["flag_inadimplente"] = (
            frame["data_pagamento"].isna() | (frame["data_pagamento"] > frame["data_vencimento"])
        ).astype(int)
        frame["mes_referencia"] = frame["data_vencimento"].dt.month
        frame["trimestre_referencia"] = frame["data_vencimento"].dt.quarter

        for months in (3, 6, 12):
            window_start = pd.Timestamp(self.observation_date - timedelta(days=30 * months))
            history = (
                frame.loc[frame["data_vencimento"] >= window_start]
                .groupby("cod_uc", dropna=False)
                .agg(
                    **{
                        f"qtd_faturas_uc_{months}m": ("cod_fatura", "count"),
                        f"taxa_inadimplencia_uc_{months}m": ("flag_inadimplente", "mean"),
                        f"media_dias_atraso_uc_{months}m": ("dias_atraso_pagamento", "mean"),
                    }
                )
                .reset_index()
            )
            frame = frame.merge(history, on="cod_uc", how="left")

        frame = frame.sort_values(["cod_uc", "data_vencimento"])
        frame["mes_inadimplente"] = frame["flag_inadimplente"].astype(int)
        frame["meses_consecutivos_inadimplente"] = (
            frame.groupby("cod_uc", dropna=False)["mes_inadimplente"]
            .transform(_count_consecutive_inadimplencia)
            .astype(int)
        )

        if cadastro_ucs is not None and not cadastro_ucs.empty:
            frame = frame.merge(cadastro_ucs, on="cod_uc", how="left")
            regional_stats = (
                frame.groupby("cod_base", dropna=False)
                .agg(
                    taxa_inadimplencia_base=("flag_inadimplente", "mean"),
                    valor_medio_base=("valor_fatura", "mean"),
                )
                .reset_index()
            )
            frame = frame.merge(regional_stats, on="cod_base", how="left")

        frame["_observation_date"] = self.observation_date.isoformat()
        numeric_columns = [
            "valor_fatura",
            "valor_pago",
            "dias_atraso_pagamento",
            "qtd_faturas_uc_3m",
            "taxa_inadimplencia_uc_3m",
            "media_dias_atraso_uc_3m",
            "qtd_faturas_uc_6m",
            "taxa_inadimplencia_uc_6m",
            "media_dias_atraso_uc_6m",
            "qtd_faturas_uc_12m",
            "taxa_inadimplencia_uc_12m",
            "media_dias_atraso_uc_12m",
            "meses_consecutivos_inadimplente",
            "taxa_inadimplencia_base",
            "valor_medio_base",
        ]
        return coalesce_numeric(frame, numeric_columns)


def _count_consecutive_inadimplencia(series: pd.Series) -> pd.Series:
    counter = 0
    values: list[int] = []
    for value in series.astype(int):
        if value == 1:
            counter += 1
        else:
            counter = 0
        values.append(counter)
    return pd.Series(values, index=series.index)
