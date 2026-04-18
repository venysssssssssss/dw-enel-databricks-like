"""Enrichment helpers for RAG/BI analytical frame.

This module enriches the complaint frame with:
1. Meter type profile by installation (SP-heavy source).
2. Invoice complaint profile by order (SP source).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class EnrichmentPaths:
    medidor_sp_path: Path
    fatura_sp_path: Path


def normalize_installation(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )


def normalize_order(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )


def build_medidor_profile(path: Path) -> pd.DataFrame:
    """Return one dominant meter type per installation."""
    if not path.exists():
        return pd.DataFrame(
            columns=[
                "instalacao",
                "tipo_medidor_dominante",
                "instalacao_multi_tipo",
                "equipamentos_unicos",
                "tipos_distintos",
            ]
        )

    frame = pd.read_csv(path, dtype=str, low_memory=False)
    if "instalacao" not in frame.columns:
        return pd.DataFrame(
            columns=[
                "instalacao",
                "tipo_medidor_dominante",
                "instalacao_multi_tipo",
                "equipamentos_unicos",
                "tipos_distintos",
            ]
        )

    frame = frame.copy()
    frame["instalacao"] = normalize_installation(frame["instalacao"])
    frame["tipo"] = frame.get("tipo", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    frame["equipamento"] = (
        frame.get("equipamento", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    )
    frame = frame.loc[frame["instalacao"].ne("")]
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "instalacao",
                "tipo_medidor_dominante",
                "instalacao_multi_tipo",
                "equipamentos_unicos",
                "tipos_distintos",
            ]
        )

    # Dominant type per installation (mode by frequency, stable tie-break by name).
    type_count = (
        frame.groupby(["instalacao", "tipo"], as_index=False)
        .size()
        .rename(columns={"size": "qtd"})
        .sort_values(["instalacao", "qtd", "tipo"], ascending=[True, False, True])
    )
    dominant = type_count.drop_duplicates(subset=["instalacao"], keep="first")
    type_stats = (
        frame.groupby("instalacao", as_index=False)
        .agg(
            tipos_distintos=("tipo", "nunique"),
            equipamentos_unicos=("equipamento", "nunique"),
        )
    )
    out = dominant.merge(type_stats, on="instalacao", how="left")
    out = out.rename(columns={"tipo": "tipo_medidor_dominante"})
    out["instalacao_multi_tipo"] = out["tipos_distintos"].fillna(0).astype(int).gt(1)
    return out[
        [
            "instalacao",
            "tipo_medidor_dominante",
            "instalacao_multi_tipo",
            "equipamentos_unicos",
            "tipos_distintos",
        ]
    ].reset_index(drop=True)


def build_fatura_profile(path: Path) -> pd.DataFrame:
    """Return invoice profile per complaint/order id (SP)."""
    if not path.exists():
        return pd.DataFrame(
            columns=[
                "ordem",
                "valor_fatura_reclamada_medio",
                "valor_fatura_reclamada_max",
                "dias_emissao_ate_reclamacao_medio",
                "dias_vencimento_ate_reclamacao_medio",
                "fat_reclamada_top",
                "qtd_faturas_reclamadas",
            ]
        )

    frame = pd.read_excel(path, dtype=str)
    if "ID_RECLAMACAO" not in frame.columns:
        return pd.DataFrame(
            columns=[
                "ordem",
                "valor_fatura_reclamada_medio",
                "valor_fatura_reclamada_max",
                "dias_emissao_ate_reclamacao_medio",
                "dias_vencimento_ate_reclamacao_medio",
                "fat_reclamada_top",
                "qtd_faturas_reclamadas",
            ]
        )

    df = frame.rename(
        columns={
            "ID_RECLAMACAO": "ordem",
            "VALOR_FAT RECLMADA": "valor_fatura_reclamada",
            "FAT_RECLAMADA": "fat_reclamada",
            "DATA_EMISSSAO_FAT": "data_emissao_fat",
            "DATA_VENCIMENTO": "data_vencimento",
            "DATA RECLAMACAO": "data_reclamacao",
        }
    ).copy()
    df["ordem"] = normalize_order(df["ordem"])
    df = df.loc[df["ordem"].ne("")]
    if df.empty:
        return pd.DataFrame(
            columns=[
                "ordem",
                "valor_fatura_reclamada_medio",
                "valor_fatura_reclamada_max",
                "dias_emissao_ate_reclamacao_medio",
                "dias_vencimento_ate_reclamacao_medio",
                "fat_reclamada_top",
                "qtd_faturas_reclamadas",
            ]
        )

    df["valor_fatura_reclamada"] = pd.to_numeric(df["valor_fatura_reclamada"], errors="coerce")
    df["data_emissao_fat"] = pd.to_datetime(df["data_emissao_fat"], errors="coerce")
    df["data_vencimento"] = pd.to_datetime(df["data_vencimento"], errors="coerce")
    df["data_reclamacao"] = pd.to_datetime(df["data_reclamacao"], errors="coerce")
    df["dias_emissao_ate_reclamacao"] = (
        df["data_reclamacao"] - df["data_emissao_fat"]
    ).dt.days.astype(float)
    df["dias_vencimento_ate_reclamacao"] = (
        df["data_reclamacao"] - df["data_vencimento"]
    ).dt.days.astype(float)
    df["fat_reclamada"] = df["fat_reclamada"].fillna("").astype(str).str.strip()

    def _mode_text(series: pd.Series) -> str:
        values = series.dropna().astype(str).str.strip()
        values = values.loc[values.ne("")]
        if values.empty:
            return ""
        return values.value_counts().index[0]

    profile = (
        df.groupby("ordem", as_index=False)
        .agg(
            valor_fatura_reclamada_medio=("valor_fatura_reclamada", "mean"),
            valor_fatura_reclamada_max=("valor_fatura_reclamada", "max"),
            dias_emissao_ate_reclamacao_medio=("dias_emissao_ate_reclamacao", "mean"),
            dias_vencimento_ate_reclamacao_medio=("dias_vencimento_ate_reclamacao", "mean"),
            fat_reclamada_top=("fat_reclamada", _mode_text),
            qtd_faturas_reclamadas=("fat_reclamada", "count"),
        )
        .reset_index(drop=True)
    )
    return profile


def apply_enrichment(
    frame: pd.DataFrame,
    *,
    medidor_profile: pd.DataFrame | None = None,
    fatura_profile: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join complaint frame with optional enrichment profiles."""
    if frame.empty:
        return frame.copy()

    out = frame.copy()
    out["instalacao"] = normalize_installation(
        out.get("instalacao", pd.Series("", index=out.index))
    )
    out["ordem"] = normalize_order(out.get("ordem", pd.Series("", index=out.index)))

    if medidor_profile is not None and not medidor_profile.empty:
        medidor = medidor_profile.copy()
        medidor["instalacao"] = normalize_installation(medidor["instalacao"])
        out = out.merge(medidor, on="instalacao", how="left")
    else:
        out["tipo_medidor_dominante"] = pd.NA
        out["instalacao_multi_tipo"] = pd.NA
        out["equipamentos_unicos"] = pd.NA
        out["tipos_distintos"] = pd.NA

    if fatura_profile is not None and not fatura_profile.empty:
        fatura = fatura_profile.copy()
        fatura["ordem"] = normalize_order(fatura["ordem"])
        out = out.merge(fatura, on="ordem", how="left")
    else:
        out["valor_fatura_reclamada_medio"] = pd.NA
        out["valor_fatura_reclamada_max"] = pd.NA
        out["dias_emissao_ate_reclamacao_medio"] = pd.NA
        out["dias_vencimento_ate_reclamacao_medio"] = pd.NA
        out["fat_reclamada_top"] = pd.NA
        out["qtd_faturas_reclamadas"] = pd.NA

    out["perfil_fatura_disponivel"] = out["valor_fatura_reclamada_medio"].notna()
    out["perfil_medidor_disponivel"] = out["tipo_medidor_dominante"].notna()
    return out

