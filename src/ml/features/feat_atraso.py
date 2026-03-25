"""Feature engineering for delivery-delay prediction."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from src.ml.features.base import BaseFeatureBuilder
from src.ml.utils import coalesce_numeric, ensure_datetime_columns, normalize_boolean


class AtrasoFeatureBuilder(BaseFeatureBuilder):
    feature_set_name = "atraso_entrega"
    entity_key = "cod_nota"
    target_columns = ("target_flag_atraso", "target_dias_atraso")

    def build(self, notas: pd.DataFrame) -> pd.DataFrame:
        self.validate_columns(
            notas,
            [
                "cod_nota",
                "cod_uc",
                "cod_base",
                "cod_colaborador",
                "data_criacao",
                "data_prevista",
                "status",
            ],
        )
        frame = ensure_datetime_columns(notas, ["data_criacao", "data_prevista", "data_execucao"])
        frame = coalesce_numeric(frame, ["historico_incidentes_12m"])
        frame["flag_impacto_faturamento"] = normalize_boolean(frame.get("flag_impacto_faturamento", False))
        frame["area_classificada_risco"] = normalize_boolean(frame.get("area_classificada_risco", False))
        frame["flag_risco_manual"] = normalize_boolean(frame.get("flag_risco_manual", False))
        frame = frame.loc[
            (frame["data_criacao"].dt.date <= self.observation_date) & (frame["status"] != "CANCELADA")
        ].copy()
        if frame.empty:
            return pd.DataFrame(columns=["cod_nota", "_observation_date", *self.target_columns])

        frame["dias_ate_vencimento"] = (
            frame["data_prevista"].dt.normalize() - frame["data_criacao"].dt.normalize()
        ).dt.days.fillna(0)
        frame["dia_semana_criacao"] = frame["data_criacao"].dt.dayofweek.fillna(0).astype(int)
        frame["dia_semana_previsto"] = frame["data_prevista"].dt.dayofweek.fillna(0).astype(int)
        frame["flag_fim_de_mes"] = frame["data_prevista"].dt.day.fillna(0).ge(25).astype(int)
        frame["flag_inicio_de_mes"] = frame["data_prevista"].dt.day.fillna(0).le(5).astype(int)

        history_90d = frame.loc[
            frame["data_criacao"] >= pd.Timestamp(self.observation_date - timedelta(days=90))
        ].copy()
        uc_history = (
            history_90d.groupby("cod_uc", dropna=False)
            .agg(
                qtd_notas_uc_90d=("cod_nota", "count"),
                taxa_atraso_uc_90d=("status", lambda values: float(values.isin(["DEVOLVIDA"]).mean())),
                media_dias_ate_vencimento_uc=("dias_ate_vencimento", "mean"),
                max_dias_ate_vencimento_uc=("dias_ate_vencimento", "max"),
                qtd_devolucoes_uc_90d=("status", lambda values: int(values.eq("DEVOLVIDA").sum())),
            )
            .reset_index()
        )
        frame = frame.merge(uc_history, on="cod_uc", how="left")

        base_stats_7d = (
            frame.loc[frame["data_criacao"] >= pd.Timestamp(self.observation_date - timedelta(days=7))]
            .groupby("cod_base", dropna=False)
            .agg(
                taxa_atraso_base_7d=("status", lambda values: float(values.isin(["DEVOLVIDA"]).mean())),
                volume_notas_base_7d=("cod_nota", "count"),
                efetividade_base_7d=("status", lambda values: float(values.isin(["EXECUTADA", "FECHADA"]).mean())),
            )
            .reset_index()
        )
        base_stats_30d = (
            frame.loc[frame["data_criacao"] >= pd.Timestamp(self.observation_date - timedelta(days=30))]
            .groupby("cod_base", dropna=False)
            .agg(
                taxa_atraso_base_30d=("status", lambda values: float(values.isin(["DEVOLVIDA"]).mean())),
                colaboradores_ativos_30d=("cod_colaborador", "nunique"),
            )
            .reset_index()
        )
        frame = frame.merge(base_stats_7d, on="cod_base", how="left").merge(
            base_stats_30d,
            on="cod_base",
            how="left",
        )

        colab_stats = (
            frame.loc[
                (frame["data_criacao"] >= pd.Timestamp(self.observation_date - timedelta(days=30)))
                & frame["cod_colaborador"].notna()
            ]
            .groupby("cod_colaborador", dropna=False)
            .agg(
                taxa_atraso_colaborador_30d=("status", lambda values: float(values.isin(["DEVOLVIDA"]).mean())),
                produtividade_colaborador_dia=("cod_nota", lambda values: float(values.count() / 30.0)),
                taxa_devolucao_colaborador_30d=("status", lambda values: float(values.eq("DEVOLVIDA").mean())),
            )
            .reset_index()
        )
        frame = frame.merge(colab_stats, on="cod_colaborador", how="left")

        denominator = frame["colaboradores_ativos_30d"].replace({0.0: 1.0}).fillna(1.0)
        frame["carga_colaboradores_base"] = frame["volume_notas_base_7d"].fillna(0.0) / denominator
        frame["target_flag_atraso"] = frame["status"].isin(["DEVOLVIDA", "REABERTA"]).astype(int)

        execution_dates = frame["data_execucao"].fillna(pd.Timestamp(self.observation_date))
        frame["target_dias_atraso"] = (
            execution_dates.dt.normalize() - frame["data_prevista"].dt.normalize()
        ).dt.days.clip(lower=0)
        frame["_observation_date"] = self.observation_date.isoformat()

        numeric_columns = [
            "dias_ate_vencimento",
            "historico_incidentes_12m",
            "qtd_notas_uc_90d",
            "taxa_atraso_uc_90d",
            "media_dias_ate_vencimento_uc",
            "max_dias_ate_vencimento_uc",
            "qtd_devolucoes_uc_90d",
            "taxa_atraso_base_7d",
            "volume_notas_base_7d",
            "efetividade_base_7d",
            "taxa_atraso_base_30d",
            "colaboradores_ativos_30d",
            "taxa_atraso_colaborador_30d",
            "produtividade_colaborador_dia",
            "taxa_devolucao_colaborador_30d",
            "carga_colaboradores_base",
            "target_dias_atraso",
        ]
        frame = coalesce_numeric(frame, numeric_columns)
        return frame
