"""Feature engineering for target-projection models."""

from __future__ import annotations

import pandas as pd

from src.ml.features.base import BaseFeatureBuilder
from src.ml.utils import coalesce_numeric


class MetasFeatureBuilder(BaseFeatureBuilder):
    feature_set_name = "metas"
    entity_key = "cod_base"
    target_columns = ("target_pct_atingimento", "target_flag_risco")

    def build(self, metas: pd.DataFrame) -> pd.DataFrame:
        self.validate_columns(
            metas,
            ["cod_base", "mes_referencia", "valor_meta", "valor_realizado"],
        )
        frame = metas.copy()
        frame["mes_referencia"] = pd.to_datetime(frame["mes_referencia"], format="%Y-%m", errors="coerce")
        frame = coalesce_numeric(frame, ["valor_meta", "valor_realizado"])
        frame = frame.loc[frame["mes_referencia"].dt.date <= self.observation_date.replace(day=1)].copy()
        if frame.empty:
            return pd.DataFrame(columns=["cod_base", "_observation_date", *self.target_columns])

        frame = frame.sort_values(["cod_base", "mes_referencia"])
        frame["pct_atingimento"] = (100.0 * frame["valor_realizado"] / frame["valor_meta"].replace({0.0: 1.0})).clip(
            lower=0.0,
            upper=200.0,
        )
        frame["lag_1_pct"] = frame.groupby("cod_base")["pct_atingimento"].shift(1)
        frame["lag_3_media_pct"] = (
            frame.groupby("cod_base")["pct_atingimento"].rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
        )
        frame["gap_meta"] = frame["valor_meta"] - frame["valor_realizado"]
        frame["tendencia_mensal"] = frame.groupby("cod_base")["pct_atingimento"].diff().fillna(0.0)
        frame["target_pct_atingimento"] = frame["pct_atingimento"]
        frame["target_flag_risco"] = frame["pct_atingimento"].lt(90.0).astype(int)
        frame["_observation_date"] = self.observation_date.isoformat()
        return coalesce_numeric(
            frame,
            [
                "pct_atingimento",
                "lag_1_pct",
                "lag_3_media_pct",
                "gap_meta",
                "tendencia_mensal",
                "target_pct_atingimento",
                "target_flag_risco",
            ],
        )
