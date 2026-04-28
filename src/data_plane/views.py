"""Declarative BI/RAG view registry for the unified data plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

import pandas as pd

from src.viz.erro_leitura_dashboard_data import (
    category_breakdown,
    classifier_coverage,
    classifier_indefinido_tokens,
    compute_kpis,
    mis_executive_summary,
    mis_monthly_mis,
    monthly_volume,
    radar_causes_by_region,
    refaturamento_by_cause,
    region_cause_matrix,
    reincidence_matrix,
    root_cause_distribution,
    severity_heatmap,
    sp_categoria_subcausa_tree,
    sp_severidade_categorias,
    sp_severidade_causas,
    sp_severidade_descricoes,
    sp_severidade_mensal,
    sp_severidade_distribution,
    sp_severidade_overview,
    sp_severidade_ranking,
    taxonomy_reference,
    topic_distribution,
)
from src.viz.reclamacoes_ce_dashboard_data import (
    cruzamento_com_erro_leitura as _ce_cruzamento_com_erro_leitura,
)
from src.viz.reclamacoes_ce_dashboard_data import (
    macro_tema_distribution as _ce_macro_tema_distribution,
)
from src.viz.reclamacoes_ce_dashboard_data import (
    monthly_trend_by_tema as _ce_monthly_trend_by_tema,
)
from src.viz.reclamacoes_ce_dashboard_data import (
    prepare_reclamacoes_ce_frame,
)


class ViewCallable(Protocol):
    def __call__(self, frame: pd.DataFrame, **kwargs: Any) -> pd.DataFrame: ...


@dataclass(frozen=True, slots=True)
class ViewSpec:
    id: str
    group_keys: tuple[str, ...]
    metrics: tuple[str, ...]
    filters_schema: tuple[str, ...] = ()
    handler: ViewCallable | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)

    def run(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.handler is None:
            raise KeyError(f"View sem handler: {self.id}")
        return self.handler(frame, **self.kwargs)


FILTER_FIELDS = (
    "regiao",
    "tipo_origem",
    "causa_canonica",
    "causa_canonica_confidence",
    "topic_name",
    "status",
    "assunto",
    "start_date",
    "end_date",
)


def _mode_text(series: pd.Series) -> str:
    values = series.dropna().astype(str).str.strip()
    values = values.loc[values.ne("")]
    if values.empty:
        return ""
    return values.value_counts().index[0]


def kpis_view(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([asdict(compute_kpis(frame))])


def by_region_view(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "regiao",
                "qtd_ordens",
                "taxa_refaturamento",
                "ordens_refaturadas",
                "causas_rotuladas",
            ]
        )
    grouped = (
        frame.groupby("regiao", as_index=False)
        .agg(
            qtd_ordens=("ordem", "nunique"),
            taxa_refaturamento=("flag_resolvido_com_refaturamento", "mean"),
            ordens_refaturadas=("flag_resolvido_com_refaturamento", "sum"),
            causas_rotuladas=("has_causa_raiz_label", "sum"),
        )
        .sort_values("qtd_ordens", ascending=False)
    )
    return grouped


def top_assunto_view(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    if frame.empty or "assunto" not in frame.columns:
        return pd.DataFrame(columns=["assunto", "qtd_ordens", "percentual"])
    grouped = (
        frame.groupby("assunto", dropna=False, as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values("qtd_ordens", ascending=False)
        .head(limit)
    )
    total = max(int(frame["ordem"].nunique()), 1)
    grouped["percentual"] = grouped["qtd_ordens"] / total
    return grouped


def top_causa_view(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["causa_canonica", "qtd_ordens", "percentual"])
    sub = frame.loc[frame["causa_canonica"].notna()]
    grouped = (
        sub.groupby("causa_canonica", dropna=False, as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values("qtd_ordens", ascending=False)
        .head(limit)
    )
    total = max(int(sub["ordem"].nunique()), 1)
    grouped["percentual"] = grouped["qtd_ordens"] / total
    return grouped


def refaturamento_summary_view(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["total", "refaturadas", "taxa_refaturamento"])
    flag = frame["flag_resolvido_com_refaturamento"].fillna(False).astype(bool)
    return pd.DataFrame(
        [
            {
                "total": int(frame["ordem"].nunique()),
                "refaturadas": int(flag.sum()),
                "taxa_refaturamento": float(flag.mean()) if len(flag) else 0.0,
            }
        ]
    )


def top_instalacoes_view(frame: pd.DataFrame, *, limit: int = 20) -> pd.DataFrame:
    cols = [
        "instalacao",
        "qtd_ordens",
        "assunto_top",
        "causa_top",
        "taxa_refaturamento",
        "tipo_medidor_dominante",
        "instalacao_multi_tipo",
    ]
    if frame.empty or "instalacao" not in frame.columns:
        return pd.DataFrame(columns=cols)
    sub = frame.loc[frame["instalacao"].notna()].copy()
    sub["instalacao"] = sub["instalacao"].astype(str)
    sub = sub.loc[sub["instalacao"].str.strip().ne("") & sub["instalacao"].str.lower().ne("nan")]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    flag = sub["flag_resolvido_com_refaturamento"].fillna(False).astype(bool)
    sub = sub.assign(_refat=flag)

    grouped = (
        sub.groupby("instalacao", as_index=False)
        .agg(
            qtd_ordens=("ordem", "nunique"),
            assunto_top=("assunto", _mode_text),
            causa_top=("causa_canonica", _mode_text),
            taxa_refaturamento=("_refat", "mean"),
            tipo_medidor_dominante=("tipo_medidor_dominante", _mode_text),
            instalacao_multi_tipo=("instalacao_multi_tipo", "max"),
        )
        .sort_values("qtd_ordens", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    return grouped[cols]


def top_instalacoes_por_regional_view(
    frame: pd.DataFrame, *, limit_per_region: int = 5
) -> pd.DataFrame:
    cols = ["regiao", "instalacao", "qtd_ordens", "assunto_top", "tipo_medidor_dominante"]
    if frame.empty or "instalacao" not in frame.columns or "regiao" not in frame.columns:
        return pd.DataFrame(columns=cols)
    sub = frame.copy()
    sub["instalacao"] = sub["instalacao"].fillna("").astype(str).str.strip()
    sub = sub.loc[sub["instalacao"].ne("")]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby(["regiao", "instalacao"], as_index=False)
        .agg(
            qtd_ordens=("ordem", "nunique"),
            assunto_top=("assunto", _mode_text),
            tipo_medidor_dominante=("tipo_medidor_dominante", _mode_text),
        )
        .sort_values(["regiao", "qtd_ordens"], ascending=[True, False])
    )
    top = (
        grouped.groupby("regiao", as_index=False, group_keys=False)
        .head(limit_per_region)
        .reset_index(drop=True)
    )
    return top[cols]


def top_instalacoes_digitacao_view(frame: pd.DataFrame, *, limit: int = 20) -> pd.DataFrame:
    cols = [
        "regiao",
        "instalacao",
        "qtd_ordens",
        "assunto_top",
        "tipo_medidor_dominante",
    ]
    if frame.empty or "instalacao" not in frame.columns or "causa_canonica" not in frame.columns:
        return pd.DataFrame(columns=cols)
    sub = frame.copy()
    causa = sub["causa_canonica"].fillna("").astype(str).str.casefold()
    texto = (
        sub.get("texto_completo", pd.Series("", index=sub.index))
        .fillna("")
        .astype(str)
        .str.casefold()
    )
    sub = sub.loc[causa.str.contains("digit") | texto.str.contains("digit")]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    sub["instalacao"] = sub["instalacao"].fillna("").astype(str).str.strip()
    sub = sub.loc[sub["instalacao"].ne("")]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby(["regiao", "instalacao"], as_index=False)
        .agg(
            qtd_ordens=("ordem", "nunique"),
            assunto_top=("assunto", _mode_text),
            tipo_medidor_dominante=("tipo_medidor_dominante", _mode_text),
        )
        .sort_values("qtd_ordens", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    return grouped[cols]


def sp_tipos_medidor_view(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    cols = [
        "regiao",
        "tipo_medidor_dominante",
        "qtd_ordens",
        "qtd_instalacoes",
        "percentual",
    ]
    if (
        frame.empty
        or "regiao" not in frame.columns
        or "tipo_medidor_dominante" not in frame.columns
    ):
        return pd.DataFrame(columns=cols)
    sp = frame.loc[frame["regiao"].astype(str) == "SP"].copy()
    if sp.empty:
        return pd.DataFrame(columns=cols)
    sp["tipo_medidor_dominante"] = sp["tipo_medidor_dominante"].fillna("").astype(str).str.strip()
    sp = sp.loc[sp["tipo_medidor_dominante"].ne("")]
    if sp.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sp.groupby("tipo_medidor_dominante", as_index=False)
        .agg(
            qtd_ordens=("ordem", "nunique"),
            qtd_instalacoes=("instalacao", "nunique"),
        )
        .sort_values("qtd_ordens", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    total = max(int(sp["ordem"].nunique()), 1)
    grouped["percentual"] = grouped["qtd_ordens"] / total
    grouped["regiao"] = "SP"
    return grouped[cols]


def sp_tipos_medidor_digitacao_view(frame: pd.DataFrame, *, limit: int = 10) -> pd.DataFrame:
    cols = [
        "regiao",
        "tipo_medidor_dominante",
        "qtd_ordens",
        "qtd_instalacoes",
        "percentual",
    ]
    if (
        frame.empty
        or "causa_canonica" not in frame.columns
        or "tipo_medidor_dominante" not in frame.columns
    ):
        return pd.DataFrame(columns=cols)
    sp = frame.loc[frame["regiao"].astype(str) == "SP"].copy()
    if sp.empty:
        return pd.DataFrame(columns=cols)
    causa = sp["causa_canonica"].fillna("").astype(str).str.casefold()
    texto = (
        sp.get("texto_completo", pd.Series("", index=sp.index))
        .fillna("")
        .astype(str)
        .str.casefold()
    )
    sp = sp.loc[causa.str.contains("digit") | texto.str.contains("digit")]
    if sp.empty:
        return pd.DataFrame(columns=cols)
    sp["tipo_medidor_dominante"] = sp["tipo_medidor_dominante"].fillna("").astype(str).str.strip()
    sp = sp.loc[sp["tipo_medidor_dominante"].ne("")]
    if sp.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sp.groupby("tipo_medidor_dominante", as_index=False)
        .agg(
            qtd_ordens=("ordem", "nunique"),
            qtd_instalacoes=("instalacao", "nunique"),
        )
        .sort_values("qtd_ordens", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    total = max(int(sp["ordem"].nunique()), 1)
    grouped["percentual"] = grouped["qtd_ordens"] / total
    grouped["regiao"] = "SP"
    return grouped[cols]


def sp_causas_por_tipo_medidor_view(
    frame: pd.DataFrame,
    *,
    top_types: int = 6,
    top_causes_per_type: int = 5,
) -> pd.DataFrame:
    cols = [
        "regiao",
        "tipo_medidor_dominante",
        "causa_canonica",
        "qtd_ordens",
        "qtd_total_tipo",
        "percentual_no_tipo",
        "rank",
    ]
    required = {"regiao", "tipo_medidor_dominante", "causa_canonica", "ordem"}
    if frame.empty or any(column not in frame.columns for column in required):
        return pd.DataFrame(columns=cols)
    sp = frame.loc[frame["regiao"].astype(str) == "SP"].copy()
    if sp.empty:
        return pd.DataFrame(columns=cols)
    sp["tipo_medidor_dominante"] = (
        sp["tipo_medidor_dominante"].fillna("").astype(str).str.strip()
    )
    sp["causa_canonica"] = sp["causa_canonica"].fillna("").astype(str).str.strip()
    sp = sp.loc[sp["tipo_medidor_dominante"].ne("") & sp["causa_canonica"].ne("")]
    if sp.empty:
        return pd.DataFrame(columns=cols)

    totals = (
        sp.groupby("tipo_medidor_dominante", as_index=False)
        .agg(qtd_total_tipo=("ordem", "nunique"))
        .sort_values("qtd_total_tipo", ascending=False)
        .head(top_types)
        .reset_index(drop=True)
    )
    if totals.empty:
        return pd.DataFrame(columns=cols)
    totals["ordem_tipo"] = range(len(totals))
    sp = sp.loc[sp["tipo_medidor_dominante"].isin(totals["tipo_medidor_dominante"])]

    grouped = (
        sp.groupby(["tipo_medidor_dominante", "causa_canonica"], as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .merge(totals, on="tipo_medidor_dominante", how="inner")
    )
    grouped["percentual_no_tipo"] = grouped["qtd_ordens"] / grouped["qtd_total_tipo"].replace(0, 1)
    grouped = grouped.sort_values(
        ["ordem_tipo", "qtd_ordens", "causa_canonica"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    grouped["rank"] = grouped.groupby("tipo_medidor_dominante").cumcount() + 1
    grouped = grouped.loc[grouped["rank"] <= top_causes_per_type].copy()
    grouped["regiao"] = "SP"
    return grouped[cols].reset_index(drop=True)


def _sp_profile_frame(frame: pd.DataFrame, required: set[str]) -> pd.DataFrame:
    if frame.empty or any(column not in frame.columns for column in required | {"regiao"}):
        return pd.DataFrame()
    sub = frame.loc[frame["regiao"].astype(str) == "SP"].copy()
    if sub.empty:
        return pd.DataFrame()
    for column in (
        "instalacao",
        "fat_reclamada_top",
        "tipo_medidor_dominante",
        "assunto",
        "causa_canonica",
        "texto_completo",
    ):
        if column not in sub.columns:
            sub[column] = pd.NA
    for column in (
        "valor_fatura_reclamada_medio",
        "valor_fatura_reclamada_max",
        "dias_emissao_ate_reclamacao_medio",
        "dias_vencimento_ate_reclamacao_medio",
    ):
        if column not in sub.columns:
            sub[column] = pd.NA
        if column in sub.columns:
            sub[column] = pd.to_numeric(sub[column], errors="coerce")
    return sub


def sp_faturas_altas_view(frame: pd.DataFrame, *, limit: int = 10) -> pd.DataFrame:
    cols = [
        "regiao",
        "instalacao",
        "fat_reclamada_top",
        "valor_fatura_reclamada_max",
        "valor_fatura_reclamada_medio",
        "dias_emissao_ate_reclamacao_medio",
        "dias_vencimento_ate_reclamacao_medio",
        "tipo_medidor_dominante",
        "assunto_top",
        "causa_top",
        "qtd_ordens",
    ]
    required = {"instalacao", "fat_reclamada_top", "valor_fatura_reclamada_max", "ordem"}
    sub = _sp_profile_frame(frame, required)
    if sub.empty:
        return pd.DataFrame(columns=cols)
    sub["instalacao"] = sub["instalacao"].fillna("").astype(str).str.strip()
    sub["fat_reclamada_top"] = sub["fat_reclamada_top"].fillna("").astype(str).str.strip()
    sub = sub.loc[
        sub["instalacao"].ne("")
        & sub["fat_reclamada_top"].ne("")
        & sub["valor_fatura_reclamada_max"].notna()
    ]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby(["instalacao", "fat_reclamada_top"], as_index=False)
        .agg(
            valor_fatura_reclamada_max=("valor_fatura_reclamada_max", "max"),
            valor_fatura_reclamada_medio=("valor_fatura_reclamada_medio", "mean"),
            dias_emissao_ate_reclamacao_medio=("dias_emissao_ate_reclamacao_medio", "mean"),
            dias_vencimento_ate_reclamacao_medio=("dias_vencimento_ate_reclamacao_medio", "mean"),
            tipo_medidor_dominante=("tipo_medidor_dominante", _mode_text),
            assunto_top=("assunto", _mode_text),
            causa_top=("causa_canonica", _mode_text),
            qtd_ordens=("ordem", "nunique"),
        )
        .sort_values("valor_fatura_reclamada_max", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    grouped["regiao"] = "SP"
    return grouped[cols]


def sp_fatura_medidor_view(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    cols = [
        "regiao",
        "tipo_medidor_dominante",
        "qtd_ordens",
        "qtd_instalacoes",
        "valor_fatura_reclamada_medio",
        "valor_fatura_reclamada_max",
        "dias_emissao_ate_reclamacao_medio",
        "dias_vencimento_ate_reclamacao_medio",
        "assunto_top",
        "causa_top",
    ]
    required = {"tipo_medidor_dominante", "valor_fatura_reclamada_medio", "ordem", "instalacao"}
    sub = _sp_profile_frame(frame, required)
    if sub.empty:
        return pd.DataFrame(columns=cols)
    sub["tipo_medidor_dominante"] = (
        sub["tipo_medidor_dominante"].fillna("").astype(str).str.strip()
    )
    sub = sub.loc[sub["tipo_medidor_dominante"].ne("")]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby("tipo_medidor_dominante", as_index=False)
        .agg(
            qtd_ordens=("ordem", "nunique"),
            qtd_instalacoes=("instalacao", "nunique"),
            valor_fatura_reclamada_medio=("valor_fatura_reclamada_medio", "mean"),
            valor_fatura_reclamada_max=("valor_fatura_reclamada_max", "max"),
            dias_emissao_ate_reclamacao_medio=("dias_emissao_ate_reclamacao_medio", "mean"),
            dias_vencimento_ate_reclamacao_medio=("dias_vencimento_ate_reclamacao_medio", "mean"),
            assunto_top=("assunto", _mode_text),
            causa_top=("causa_canonica", _mode_text),
        )
        .sort_values(["qtd_ordens", "valor_fatura_reclamada_max"], ascending=[False, False])
        .head(limit)
        .reset_index(drop=True)
    )
    grouped["regiao"] = "SP"
    return grouped[cols]


def sp_digitacao_fatura_medidor_view(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    cols = [
        "regiao",
        "tipo_medidor_dominante",
        "qtd_ordens",
        "qtd_instalacoes",
        "valor_fatura_reclamada_medio",
        "valor_fatura_reclamada_max",
        "dias_emissao_ate_reclamacao_medio",
        "dias_vencimento_ate_reclamacao_medio",
        "assunto_top",
    ]
    required = {"tipo_medidor_dominante", "causa_canonica", "valor_fatura_reclamada_medio", "ordem"}
    sub = _sp_profile_frame(frame, required)
    if sub.empty:
        return pd.DataFrame(columns=cols)
    causa = sub["causa_canonica"].fillna("").astype(str).str.casefold()
    texto = (
        sub.get("texto_completo", pd.Series("", index=sub.index))
        .fillna("")
        .astype(str)
        .str.casefold()
    )
    sub = sub.loc[causa.str.contains("digit") | texto.str.contains("digit")]
    sub["tipo_medidor_dominante"] = (
        sub["tipo_medidor_dominante"].fillna("").astype(str).str.strip()
    )
    sub = sub.loc[sub["tipo_medidor_dominante"].ne("")]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby("tipo_medidor_dominante", as_index=False)
        .agg(
            qtd_ordens=("ordem", "nunique"),
            qtd_instalacoes=("instalacao", "nunique"),
            valor_fatura_reclamada_medio=("valor_fatura_reclamada_medio", "mean"),
            valor_fatura_reclamada_max=("valor_fatura_reclamada_max", "max"),
            dias_emissao_ate_reclamacao_medio=("dias_emissao_ate_reclamacao_medio", "mean"),
            dias_vencimento_ate_reclamacao_medio=("dias_vencimento_ate_reclamacao_medio", "mean"),
            assunto_top=("assunto", _mode_text),
        )
        .sort_values(["qtd_ordens", "valor_fatura_reclamada_max"], ascending=[False, False])
        .head(limit)
        .reset_index(drop=True)
    )
    grouped["regiao"] = "SP"
    return grouped[cols]


def sp_medidores_problema_reclamacao_view(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    cols = [
        "regiao",
        "tipo_medidor_dominante",
        "assunto_top",
        "causa_top",
        "qtd_ordens",
        "qtd_instalacoes",
        "valor_fatura_reclamada_medio",
        "valor_fatura_reclamada_max",
        "dias_emissao_ate_reclamacao_medio",
    ]
    required = {"tipo_medidor_dominante", "ordem", "instalacao"}
    sub = _sp_profile_frame(frame, required)
    if sub.empty:
        return pd.DataFrame(columns=cols)
    sub["tipo_medidor_dominante"] = (
        sub["tipo_medidor_dominante"].fillna("").astype(str).str.strip()
    )
    sub = sub.loc[sub["tipo_medidor_dominante"].ne("")]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby("tipo_medidor_dominante", as_index=False)
        .agg(
            assunto_top=("assunto", _mode_text),
            causa_top=("causa_canonica", _mode_text),
            qtd_ordens=("ordem", "nunique"),
            qtd_instalacoes=("instalacao", "nunique"),
            valor_fatura_reclamada_medio=("valor_fatura_reclamada_medio", "mean"),
            valor_fatura_reclamada_max=("valor_fatura_reclamada_max", "max"),
            dias_emissao_ate_reclamacao_medio=("dias_emissao_ate_reclamacao_medio", "mean"),
        )
        .sort_values(["qtd_ordens", "qtd_instalacoes"], ascending=[False, False])
        .head(limit)
        .reset_index(drop=True)
    )
    grouped["regiao"] = "SP"
    return grouped[cols]


def ce_total_assunto_causa_view(
    frame: pd.DataFrame,
    *,
    top_assuntos: int = 6,
    top_causas_por_assunto: int = 4,
) -> pd.DataFrame:
    cols = [
        "regiao",
        "assunto",
        "causa_canonica",
        "qtd_ordens",
        "qtd_assunto",
        "percentual_no_assunto",
        "rank_assunto",
        "rank_causa",
    ]
    required = {"regiao", "tipo_origem", "assunto", "causa_canonica", "ordem"}
    if frame.empty or any(column not in frame.columns for column in required):
        return pd.DataFrame(columns=cols)
    sub = frame.loc[
        (frame["regiao"].astype(str) == "CE")
        & (frame["tipo_origem"].astype(str) == "reclamacao_total")
    ].copy()
    if sub.empty:
        return pd.DataFrame(columns=cols)
    sub["assunto"] = sub["assunto"].fillna("").astype(str).str.strip()
    sub["causa_canonica"] = sub["causa_canonica"].fillna("").astype(str).str.strip()
    sub = sub.loc[sub["assunto"].ne("") & sub["causa_canonica"].ne("")]
    if sub.empty:
        return pd.DataFrame(columns=cols)

    top = (
        sub.groupby("assunto", as_index=False)
        .agg(qtd_assunto=("ordem", "nunique"))
        .sort_values("qtd_assunto", ascending=False)
        .head(top_assuntos)
        .reset_index(drop=True)
    )
    if top.empty:
        return pd.DataFrame(columns=cols)
    top["rank_assunto"] = range(1, len(top) + 1)
    sub = sub.loc[sub["assunto"].isin(top["assunto"])]
    grouped = (
        sub.groupby(["assunto", "causa_canonica"], as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .merge(top, on="assunto", how="inner")
    )
    grouped["percentual_no_assunto"] = grouped["qtd_ordens"] / grouped["qtd_assunto"].replace(0, 1)
    grouped = grouped.sort_values(
        ["rank_assunto", "qtd_ordens", "causa_canonica"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    grouped["rank_causa"] = grouped.groupby("assunto").cumcount() + 1
    grouped = grouped.loc[grouped["rank_causa"] <= top_causas_por_assunto]
    grouped["regiao"] = "CE"
    return grouped[cols].reset_index(drop=True)


def motivos_taxonomia_view(frame: pd.DataFrame, *, limit: int = 20) -> pd.DataFrame:
    cols = [
        "regiao",
        "assunto",
        "causa_canonica",
        "motivo_taxonomia",
        "qtd_ordens",
        "percentual",
    ]
    required = {"regiao", "assunto", "causa_canonica", "ordem"}
    if frame.empty or any(column not in frame.columns for column in required):
        return pd.DataFrame(columns=cols)
    sub = frame.copy()
    sub["regiao"] = sub["regiao"].fillna("").astype(str).str.strip()
    sub["assunto"] = sub["assunto"].fillna("").astype(str).str.strip()
    sub["causa_canonica"] = sub["causa_canonica"].fillna("").astype(str).str.strip()
    sub = sub.loc[sub["regiao"].isin({"CE", "SP"})]
    sub = sub.loc[sub["assunto"].ne("") & sub["causa_canonica"].ne("")]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby(["regiao", "assunto", "causa_canonica"], as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values("qtd_ordens", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    total = max(int(sub["ordem"].nunique()), 1)
    grouped["motivo_taxonomia"] = grouped["assunto"] + " | " + grouped["causa_canonica"]
    grouped["percentual"] = grouped["qtd_ordens"] / total
    return grouped[cols]


def monthly_assunto_breakdown_view(
    frame: pd.DataFrame, *, top_per_month: int = 3, max_months: int = 18
) -> pd.DataFrame:
    cols = ["mes_ingresso", "assunto", "qtd_ordens", "rank"]
    if frame.empty or "mes_ingresso" not in frame.columns or "assunto" not in frame.columns:
        return pd.DataFrame(columns=cols)
    sub = frame.loc[frame["mes_ingresso"].notna() & frame["assunto"].notna()]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby(["mes_ingresso", "assunto"], as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
    )
    grouped["rank"] = (
        grouped.sort_values(["mes_ingresso", "qtd_ordens"], ascending=[True, False])
        .groupby("mes_ingresso")
        .cumcount()
        + 1
    )
    grouped = grouped.loc[grouped["rank"] <= top_per_month]
    months = sorted(grouped["mes_ingresso"].dropna().unique())[-max_months:]
    grouped = grouped.loc[grouped["mes_ingresso"].isin(months)]
    return grouped.sort_values(["mes_ingresso", "rank"]).reset_index(drop=True)[cols]


def monthly_causa_breakdown_view(
    frame: pd.DataFrame, *, top_per_month: int = 3, max_months: int = 18
) -> pd.DataFrame:
    cols = ["mes_ingresso", "causa_canonica", "qtd_ordens", "rank"]
    if (
        frame.empty
        or "mes_ingresso" not in frame.columns
        or "causa_canonica" not in frame.columns
    ):
        return pd.DataFrame(columns=cols)
    sub = frame.loc[frame["mes_ingresso"].notna() & frame["causa_canonica"].notna()]
    if "has_causa_raiz_label" in sub.columns:
        label = sub["has_causa_raiz_label"].fillna(False).astype(bool)
        sub = sub.loc[label]
    sub = sub.loc[
        ~sub["causa_canonica"].astype(str).str.lower().str.contains("sem_causa", na=False)
    ]
    if sub.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        sub.groupby(["mes_ingresso", "causa_canonica"], as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
    )
    grouped["rank"] = (
        grouped.sort_values(["mes_ingresso", "qtd_ordens"], ascending=[True, False])
        .groupby("mes_ingresso")
        .cumcount()
        + 1
    )
    grouped = grouped.loc[grouped["rank"] <= top_per_month]
    months = sorted(grouped["mes_ingresso"].dropna().unique())[-max_months:]
    grouped = grouped.loc[grouped["mes_ingresso"].isin(months)]
    return grouped.sort_values(["mes_ingresso", "rank"]).reset_index(drop=True)[cols]


def sp_causa_observacoes_view(frame: pd.DataFrame, *, sample_size: int = 3) -> pd.DataFrame:
    cols = [
        "regiao",
        "causa_lider",
        "qtd_ordens",
        "percentual",
        "assunto_top",
        "observacoes_exemplo",
    ]
    if frame.empty or "regiao" not in frame.columns or "causa_canonica" not in frame.columns:
        return pd.DataFrame(columns=cols)
    sp = frame.loc[frame["regiao"].astype(str) == "SP"].copy()
    if sp.empty:
        return pd.DataFrame(columns=cols)
    counts = (
        sp.groupby("causa_canonica", as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values("qtd_ordens", ascending=False)
    )
    labeled = counts.loc[~counts["causa_canonica"].astype(str).str.casefold().eq("indefinido")]
    chosen = labeled.iloc[0] if not labeled.empty else counts.iloc[0]
    cause = str(chosen["causa_canonica"])
    qtd = int(chosen["qtd_ordens"])
    total = max(int(sp["ordem"].nunique()), 1)
    cause_rows = sp.loc[sp["causa_canonica"].astype(str) == cause]
    assunto_top = _mode_text(cause_rows.get("assunto", pd.Series(dtype=str)))
    obs = (
        cause_rows.get("texto_completo", pd.Series(dtype=str))
        .fillna("")
        .astype(str)
        .str.strip()
    )
    obs = obs.loc[obs.ne("")].drop_duplicates().head(sample_size)
    snippets = " | ".join(text[:180] for text in obs.tolist()) if not obs.empty else ""
    return pd.DataFrame(
        [
            {
                "regiao": "SP",
                "causa_lider": cause,
                "qtd_ordens": qtd,
                "percentual": qtd / total,
                "assunto_top": assunto_top,
                "observacoes_exemplo": snippets,
            }
        ]
    )


def sp_perfil_assunto_lider_view(frame: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "regiao",
        "assunto_lider",
        "qtd_ordens",
        "percentual",
        "fat_reclamada_top",
        "dias_emissao_ate_reclamacao_medio",
        "tipo_medidor_dominante",
        "valor_fatura_reclamada_medio",
        "cobertura_fatura_pct",
        "cobertura_medidor_pct",
    ]
    if frame.empty or "regiao" not in frame.columns or "assunto" not in frame.columns:
        return pd.DataFrame(columns=cols)
    sp = frame.loc[frame["regiao"].astype(str) == "SP"].copy()
    if sp.empty:
        return pd.DataFrame(columns=cols)
    topic = (
        sp.groupby("assunto", as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values("qtd_ordens", ascending=False)
    )
    if topic.empty:
        return pd.DataFrame(columns=cols)
    lead = topic.iloc[0]
    assunto = str(lead["assunto"])
    qtd = int(lead["qtd_ordens"])
    total = max(int(sp["ordem"].nunique()), 1)
    sub = sp.loc[sp["assunto"].astype(str) == assunto]
    return pd.DataFrame(
        [
            {
                "regiao": "SP",
                "assunto_lider": assunto,
                "qtd_ordens": qtd,
                "percentual": qtd / total,
                "fat_reclamada_top": _mode_text(sub.get("fat_reclamada_top", pd.Series(dtype=str))),
                "dias_emissao_ate_reclamacao_medio": float(
                    pd.to_numeric(
                        sub.get("dias_emissao_ate_reclamacao_medio", pd.Series(dtype=float)),
                        errors="coerce",
                    ).mean()
                )
                if not sub.empty
                else 0.0,
                "tipo_medidor_dominante": _mode_text(
                    sub.get("tipo_medidor_dominante", pd.Series(dtype=str))
                ),
                "valor_fatura_reclamada_medio": float(
                    pd.to_numeric(
                        sub.get("valor_fatura_reclamada_medio", pd.Series(dtype=float)),
                        errors="coerce",
                    ).mean()
                )
                if not sub.empty
                else 0.0,
                "cobertura_fatura_pct": float(
                    sub.get("perfil_fatura_disponivel", pd.Series(False)).mean()
                ),
                "cobertura_medidor_pct": float(
                    sub.get("perfil_medidor_disponivel", pd.Series(False)).mean()
                ),
            }
        ]
    )


def sazonalidade_reclamacoes_view(frame: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "regiao",
        "mes_pico",
        "qtd_pico",
        "media_mensal",
        "indice_sazonal_pico",
    ]
    if frame.empty or "mes_ingresso" not in frame.columns or "regiao" not in frame.columns:
        return pd.DataFrame(columns=cols)
    monthly = (
        frame.dropna(subset=["mes_ingresso"])
        .groupby(["regiao", "mes_ingresso"], as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
    )
    if monthly.empty:
        return pd.DataFrame(columns=cols)
    rows: list[dict[str, object]] = []
    for region, group in monthly.groupby("regiao"):
        group = group.sort_values("mes_ingresso")
        peak = group.sort_values("qtd_ordens", ascending=False).iloc[0]
        mean = float(group["qtd_ordens"].mean()) if not group.empty else 0.0
        peak_month = peak["mes_ingresso"]
        label = (
            peak_month.strftime("%Y-%m")
            if hasattr(peak_month, "strftime")
            else str(peak_month)[:7]
        )
        rows.append(
            {
                "regiao": region,
                "mes_pico": label,
                "qtd_pico": int(peak["qtd_ordens"]),
                "media_mensal": mean,
                "indice_sazonal_pico": (int(peak["qtd_ordens"]) / mean) if mean else 0.0,
            }
        )
    return pd.DataFrame(rows, columns=cols).sort_values("regiao").reset_index(drop=True)


def reincidencia_por_assunto_view(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    cols = [
        "assunto",
        "qtd_ordens",
        "qtd_instalacoes",
        "qtd_instalacoes_reincidentes",
        "taxa_reincidencia",
    ]
    if frame.empty or "assunto" not in frame.columns or "instalacao" not in frame.columns:
        return pd.DataFrame(columns=cols)
    sub = frame.copy()
    sub["instalacao"] = sub["instalacao"].fillna("").astype(str).str.strip()
    sub["assunto"] = sub["assunto"].fillna("").astype(str).str.strip()
    sub = sub.loc[sub["instalacao"].ne("") & sub["assunto"].ne("")]
    if sub.empty:
        return pd.DataFrame(columns=cols)

    counts = (
        sub.groupby(["assunto", "instalacao"], as_index=False)
        .agg(qtd_ordens_instalacao=("ordem", "nunique"))
    )
    agg = (
        counts.groupby("assunto", as_index=False)
        .agg(
            qtd_instalacoes=("instalacao", "nunique"),
            qtd_instalacoes_reincidentes=("qtd_ordens_instalacao", lambda s: int((s >= 2).sum())),
        )
    )
    ordens = sub.groupby("assunto", as_index=False).agg(qtd_ordens=("ordem", "nunique"))
    out = ordens.merge(agg, on="assunto", how="left")
    out["taxa_reincidencia"] = (
        out["qtd_instalacoes_reincidentes"] / out["qtd_instalacoes"].replace(0, 1)
    )
    return (
        out.sort_values(
            ["taxa_reincidencia", "qtd_instalacoes_reincidentes"],
            ascending=[False, False],
        )
        .head(limit)
        .reset_index(drop=True)[cols]
    )


_ACTION_PLAYBOOK: tuple[tuple[str, str, str], ...] = (
    ("refatur", "Revisar regra e comunicação de faturamento", "Alta"),
    ("leitura", "Priorizar inspeção de medição e tratativa de leitura", "Alta"),
    ("grupo", "Auditar enquadramento tarifário e histórico de mudanças", "Média"),
    ("estimativa", "Reduzir estimativas com coleta e validação adicional", "Média"),
    ("fatura", "Aprimorar jornada de emissão/entrega e contestação", "Média"),
)


def playbook_dificuldade_acoes_view(frame: pd.DataFrame) -> pd.DataFrame:
    cols = ["dificuldade_principal", "medida_recomendada", "prioridade"]
    if frame.empty or "assunto" not in frame.columns or "causa_canonica" not in frame.columns:
        return pd.DataFrame(columns=cols)
    top_assunto = (
        frame.groupby("assunto", as_index=False)
        .agg(qtd=("ordem", "nunique"))
        .sort_values("qtd", ascending=False)
    )
    top_causa = (
        frame.groupby("causa_canonica", as_index=False)
        .agg(qtd=("ordem", "nunique"))
        .sort_values("qtd", ascending=False)
    )
    assunto = str(top_assunto.iloc[0]["assunto"]) if not top_assunto.empty else ""
    causa = str(top_causa.iloc[0]["causa_canonica"]) if not top_causa.empty else ""
    text = f"{assunto} {causa}".lower()

    for pattern, action, priority in _ACTION_PLAYBOOK:
        if pattern in text:
            return pd.DataFrame(
                [
                    {
                        "dificuldade_principal": f"{assunto} / {causa}".strip(" /"),
                        "medida_recomendada": action,
                        "prioridade": priority,
                    }
                ],
                columns=cols,
            )
    return pd.DataFrame(
        [
            {
                "dificuldade_principal": f"{assunto} / {causa}".strip(" /"),
                "medida_recomendada": "Investigar raiz operacional e ajustar playbook local",
                "prioridade": "Média",
            }
        ],
        columns=cols,
    )


def by_group_view(frame: pd.DataFrame, *, limit: int = 6) -> pd.DataFrame:
    if frame.empty or "grupo" not in frame.columns:
        return pd.DataFrame(columns=["grupo", "qtd_ordens", "percentual"])
    grouped = (
        frame.assign(grupo=frame["grupo"].fillna("(nao informado)").astype(str))
        .groupby("grupo", as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values("qtd_ordens", ascending=False)
        .head(limit)
    )
    total = max(int(frame["ordem"].nunique()), 1)
    grouped["percentual"] = grouped["qtd_ordens"] / total
    return grouped


VIEW_REGISTRY: dict[str, ViewSpec] = {
    "kpis": ViewSpec("kpis", (), ("*",), FILTER_FIELDS, kpis_view),
    "overview": ViewSpec("overview", (), ("*",), FILTER_FIELDS, kpis_view),
    "by_region": ViewSpec("by_region", ("regiao",), ("qtd_ordens",), FILTER_FIELDS, by_region_view),
    "top_assuntos": ViewSpec(
        "top_assuntos", ("assunto",), ("qtd_ordens",), FILTER_FIELDS, top_assunto_view
    ),
    "top_causas": ViewSpec(
        "top_causas", ("causa_canonica",), ("qtd_ordens",), FILTER_FIELDS, top_causa_view
    ),
    "refaturamento_summary": ViewSpec(
        "refaturamento_summary", (), ("refaturadas",), FILTER_FIELDS, refaturamento_summary_view
    ),
    "by_group": ViewSpec("by_group", ("grupo",), ("qtd_ordens",), FILTER_FIELDS, by_group_view),
    "monthly_volume": ViewSpec(
        "monthly_volume", ("mes_ingresso", "regiao"), ("qtd_erros",), FILTER_FIELDS, monthly_volume
    ),
    "root_cause_distribution": ViewSpec(
        "root_cause_distribution",
        ("causa_canonica",),
        ("qtd_erros", "taxa_refaturamento"),
        FILTER_FIELDS,
        root_cause_distribution,
    ),
    "region_cause_matrix": ViewSpec(
        "region_cause_matrix",
        ("causa_canonica", "regiao"),
        ("qtd_erros",),
        FILTER_FIELDS,
        region_cause_matrix,
    ),
    "topic_distribution": ViewSpec(
        "topic_distribution", ("topic_name",), ("qtd_erros",), FILTER_FIELDS, topic_distribution
    ),
    "refaturamento_by_cause": ViewSpec(
        "refaturamento_by_cause",
        ("causa_canonica",),
        ("qtd_erros", "taxa_refaturamento"),
        FILTER_FIELDS,
        refaturamento_by_cause,
    ),
    "radar_causes_by_region": ViewSpec(
        "radar_causes_by_region",
        ("regiao", "causa_canonica"),
        ("percentual",),
        FILTER_FIELDS,
        radar_causes_by_region,
    ),
    "category_breakdown": ViewSpec(
        "category_breakdown",
        ("categoria", "regiao"),
        ("qtd_erros",),
        FILTER_FIELDS,
        category_breakdown,
    ),
    "severity_heatmap": ViewSpec(
        "severity_heatmap",
        ("regiao", "severidade"),
        ("qtd_erros",),
        FILTER_FIELDS,
        severity_heatmap,
    ),
    "mis": ViewSpec("mis", ("regiao",), ("*",), FILTER_FIELDS, mis_executive_summary),
    "mis_executive_summary": ViewSpec(
        "mis_executive_summary", ("regiao",), ("*",), FILTER_FIELDS, mis_executive_summary
    ),
    "mis_monthly_mis": ViewSpec(
        "mis_monthly_mis",
        ("mes_ingresso", "regiao"),
        ("qtd_erros", "mom"),
        FILTER_FIELDS,
        mis_monthly_mis,
    ),
    "classifier_coverage": ViewSpec(
        "classifier_coverage",
        ("regiao", "causa_canonica_confidence"),
        ("qtd_ordens", "percentual"),
        FILTER_FIELDS,
        classifier_coverage,
    ),
    "classifier_indefinido_tokens": ViewSpec(
        "classifier_indefinido_tokens",
        ("token",),
        ("qtd_ocorrencias",),
        FILTER_FIELDS,
        classifier_indefinido_tokens,
    ),
    "sp_severidade_distribution": ViewSpec(
        "sp_severidade_distribution",
        ("severidade",),
        ("qtd_erros", "procedentes", "improcedentes", "pct"),
        FILTER_FIELDS,
        sp_severidade_distribution,
    ),
    "sp_severidade_alta_overview": ViewSpec(
        "sp_severidade_alta_overview",
        (),
        ("total", "procedentes", "improcedentes", "valor_medio_fatura"),
        FILTER_FIELDS,
        sp_severidade_overview,
        {"severidade": "high"},
    ),
    "sp_severidade_critica_overview": ViewSpec(
        "sp_severidade_critica_overview",
        (),
        ("total", "procedentes", "improcedentes", "valor_medio_fatura"),
        FILTER_FIELDS,
        sp_severidade_overview,
        {"severidade": "critical"},
    ),
    "sp_severidade_alta_mensal": ViewSpec(
        "sp_severidade_alta_mensal",
        ("mes_ingresso",),
        ("qtd_erros", "procedentes", "improcedentes"),
        FILTER_FIELDS,
        sp_severidade_mensal,
        {"severidade": "high"},
    ),
    "sp_severidade_critica_mensal": ViewSpec(
        "sp_severidade_critica_mensal",
        ("mes_ingresso",),
        ("qtd_erros", "procedentes", "improcedentes"),
        FILTER_FIELDS,
        sp_severidade_mensal,
        {"severidade": "critical"},
    ),
    "sp_severidade_alta_categorias": ViewSpec(
        "sp_severidade_alta_categorias",
        ("categoria",),
        ("vol", "pct"),
        FILTER_FIELDS,
        sp_severidade_categorias,
        {"severidade": "high"},
    ),
    "sp_severidade_critica_categorias": ViewSpec(
        "sp_severidade_critica_categorias",
        ("categoria",),
        ("vol", "pct"),
        FILTER_FIELDS,
        sp_severidade_categorias,
        {"severidade": "critical"},
    ),
    "sp_severidade_alta_causas": ViewSpec(
        "sp_severidade_alta_causas",
        ("nome",),
        ("vol", "proc", "reinc"),
        FILTER_FIELDS,
        sp_severidade_causas,
        {"severidade": "high"},
    ),
    "sp_severidade_critica_causas": ViewSpec(
        "sp_severidade_critica_causas",
        ("nome",),
        ("vol", "proc", "reinc"),
        FILTER_FIELDS,
        sp_severidade_causas,
        {"severidade": "critical"},
    ),
    "sp_severidade_alta_ranking": ViewSpec(
        "sp_severidade_alta_ranking",
        ("inst",),
        ("reinc", "valor"),
        FILTER_FIELDS,
        sp_severidade_ranking,
        {"severidade": "high"},
    ),
    "sp_severidade_critica_ranking": ViewSpec(
        "sp_severidade_critica_ranking",
        ("inst",),
        ("reinc", "valor"),
        FILTER_FIELDS,
        sp_severidade_ranking,
        {"severidade": "critical"},
    ),
    "sp_severidade_alta_descricoes": ViewSpec(
        "sp_severidade_alta_descricoes",
        ("id",),
        ("valor",),
        FILTER_FIELDS,
        sp_severidade_descricoes,
        {"severidade": "high", "limit": 10},
    ),
    "sp_severidade_critica_descricoes": ViewSpec(
        "sp_severidade_critica_descricoes",
        ("id",),
        ("valor",),
        FILTER_FIELDS,
        sp_severidade_descricoes,
        {"severidade": "critical", "limit": 10},
    ),
    "sp_severidade_demais_overview": ViewSpec(
        "sp_severidade_demais_overview",
        (),
        ("total", "procedentes", "improcedentes", "valor_medio_fatura"),
        FILTER_FIELDS,
        sp_severidade_overview,
        {"severidade": ("medium", "low")},
    ),
    "sp_severidade_demais_mensal": ViewSpec(
        "sp_severidade_demais_mensal",
        ("mes_ingresso",),
        ("qtd_erros", "procedentes", "improcedentes"),
        FILTER_FIELDS,
        sp_severidade_mensal,
        {"severidade": ("medium", "low")},
    ),
    "sp_severidade_demais_categorias": ViewSpec(
        "sp_severidade_demais_categorias",
        ("categoria",),
        ("vol", "pct"),
        FILTER_FIELDS,
        sp_severidade_categorias,
        {"severidade": ("medium", "low")},
    ),
    "sp_severidade_demais_causas": ViewSpec(
        "sp_severidade_demais_causas",
        ("nome",),
        ("vol", "proc", "reinc"),
        FILTER_FIELDS,
        sp_severidade_causas,
        {"severidade": ("medium", "low")},
    ),
    "sp_severidade_demais_ranking": ViewSpec(
        "sp_severidade_demais_ranking",
        ("inst",),
        ("reinc", "valor"),
        FILTER_FIELDS,
        sp_severidade_ranking,
        {"severidade": ("medium", "low")},
    ),
    "sp_severidade_demais_descricoes": ViewSpec(
        "sp_severidade_demais_descricoes",
        ("id",),
        ("valor",),
        FILTER_FIELDS,
        sp_severidade_descricoes,
        {"severidade": ("medium", "low"), "limit": 10},
    ),
    "sp_categoria_subcausa_tree_alta": ViewSpec(
        "sp_categoria_subcausa_tree_alta",
        ("categoria_id", "subcausa_id"),
        ("qtd", "percentual_na_categoria", "procedentes", "improcedentes"),
        FILTER_FIELDS,
        sp_categoria_subcausa_tree,
        {"severidade": "high"},
    ),
    "sp_categoria_subcausa_tree_critica": ViewSpec(
        "sp_categoria_subcausa_tree_critica",
        ("categoria_id", "subcausa_id"),
        ("qtd", "percentual_na_categoria", "procedentes", "improcedentes"),
        FILTER_FIELDS,
        sp_categoria_subcausa_tree,
        {"severidade": "critical"},
    ),
    "sp_categoria_subcausa_tree_demais": ViewSpec(
        "sp_categoria_subcausa_tree_demais",
        ("categoria_id", "subcausa_id"),
        ("qtd", "percentual_na_categoria", "procedentes", "improcedentes"),
        FILTER_FIELDS,
        sp_categoria_subcausa_tree,
        {"severidade": ("medium", "low")},
    ),
    "sp_categoria_subcausa_tree": ViewSpec(
        "sp_categoria_subcausa_tree",
        ("categoria_id", "subcausa_id"),
        ("qtd", "percentual_na_categoria", "procedentes", "improcedentes"),
        FILTER_FIELDS,
        sp_categoria_subcausa_tree,
        {"severidade": ("high", "critical", "medium", "low")},
    ),
    "reincidence_matrix": ViewSpec(
        "reincidence_matrix",
        ("regiao", "faixa"),
        ("qtd_instalacoes",),
        FILTER_FIELDS,
        reincidence_matrix,
    ),
    "taxonomy_reference": ViewSpec(
        "taxonomy_reference", ("Categoria",), ("Peso",), (), lambda _frame: taxonomy_reference()
    ),
    "top_instalacoes": ViewSpec(
        "top_instalacoes",
        ("instalacao",),
        ("qtd_ordens", "taxa_refaturamento"),
        FILTER_FIELDS,
        top_instalacoes_view,
    ),
    "top_instalacoes_por_regional": ViewSpec(
        "top_instalacoes_por_regional",
        ("regiao", "instalacao"),
        ("qtd_ordens",),
        FILTER_FIELDS,
        top_instalacoes_por_regional_view,
    ),
    "top_instalacoes_digitacao": ViewSpec(
        "top_instalacoes_digitacao",
        ("regiao", "instalacao"),
        ("qtd_ordens",),
        FILTER_FIELDS,
        top_instalacoes_digitacao_view,
    ),
    "sp_tipos_medidor": ViewSpec(
        "sp_tipos_medidor",
        ("tipo_medidor_dominante",),
        ("qtd_ordens", "percentual"),
        FILTER_FIELDS,
        sp_tipos_medidor_view,
    ),
    "sp_tipos_medidor_digitacao": ViewSpec(
        "sp_tipos_medidor_digitacao",
        ("tipo_medidor_dominante",),
        ("qtd_ordens", "percentual"),
        FILTER_FIELDS,
        sp_tipos_medidor_digitacao_view,
    ),
    "sp_causas_por_tipo_medidor": ViewSpec(
        "sp_causas_por_tipo_medidor",
        ("tipo_medidor_dominante", "causa_canonica"),
        ("qtd_ordens", "percentual_no_tipo"),
        FILTER_FIELDS,
        sp_causas_por_tipo_medidor_view,
    ),
    "sp_faturas_altas": ViewSpec(
        "sp_faturas_altas",
        ("instalacao", "fat_reclamada_top"),
        ("valor_fatura_reclamada_max", "qtd_ordens"),
        FILTER_FIELDS,
        sp_faturas_altas_view,
    ),
    "sp_fatura_medidor": ViewSpec(
        "sp_fatura_medidor",
        ("tipo_medidor_dominante",),
        ("qtd_ordens", "valor_fatura_reclamada_medio"),
        FILTER_FIELDS,
        sp_fatura_medidor_view,
    ),
    "sp_digitacao_fatura_medidor": ViewSpec(
        "sp_digitacao_fatura_medidor",
        ("tipo_medidor_dominante",),
        ("qtd_ordens", "valor_fatura_reclamada_medio"),
        FILTER_FIELDS,
        sp_digitacao_fatura_medidor_view,
    ),
    "sp_medidores_problema_reclamacao": ViewSpec(
        "sp_medidores_problema_reclamacao",
        ("tipo_medidor_dominante",),
        ("qtd_ordens", "assunto_top"),
        FILTER_FIELDS,
        sp_medidores_problema_reclamacao_view,
    ),
    "ce_total_assunto_causa": ViewSpec(
        "ce_total_assunto_causa",
        ("assunto", "causa_canonica"),
        ("qtd_ordens", "percentual_no_assunto"),
        FILTER_FIELDS,
        ce_total_assunto_causa_view,
    ),
    "motivos_taxonomia": ViewSpec(
        "motivos_taxonomia",
        ("regiao", "assunto", "causa_canonica"),
        ("qtd_ordens", "percentual"),
        FILTER_FIELDS,
        motivos_taxonomia_view,
    ),
    "monthly_assunto_breakdown": ViewSpec(
        "monthly_assunto_breakdown",
        ("mes_ingresso", "assunto"),
        ("qtd_ordens", "rank"),
        FILTER_FIELDS,
        monthly_assunto_breakdown_view,
    ),
    "monthly_causa_breakdown": ViewSpec(
        "monthly_causa_breakdown",
        ("mes_ingresso", "causa_canonica"),
        ("qtd_ordens", "rank"),
        FILTER_FIELDS,
        monthly_causa_breakdown_view,
    ),
    "sp_causa_observacoes": ViewSpec(
        "sp_causa_observacoes",
        ("regiao", "causa_lider"),
        ("qtd_ordens", "percentual"),
        FILTER_FIELDS,
        sp_causa_observacoes_view,
    ),
    "sp_perfil_assunto_lider": ViewSpec(
        "sp_perfil_assunto_lider",
        ("regiao", "assunto_lider"),
        ("qtd_ordens", "percentual"),
        FILTER_FIELDS,
        sp_perfil_assunto_lider_view,
    ),
    "sazonalidade_reclamacoes": ViewSpec(
        "sazonalidade_reclamacoes",
        ("regiao", "mes_pico"),
        ("qtd_pico", "indice_sazonal_pico"),
        FILTER_FIELDS,
        sazonalidade_reclamacoes_view,
    ),
    "reincidencia_por_assunto": ViewSpec(
        "reincidencia_por_assunto",
        ("assunto",),
        ("qtd_instalacoes_reincidentes", "taxa_reincidencia"),
        FILTER_FIELDS,
        reincidencia_por_assunto_view,
    ),
    "playbook_dificuldade_acoes": ViewSpec(
        "playbook_dificuldade_acoes",
        ("dificuldade_principal",),
        ("prioridade",),
        FILTER_FIELDS,
        playbook_dificuldade_acoes_view,
    ),
    "ce_macro_distribution": ViewSpec(
        "ce_macro_distribution",
        ("macro_tema_label",),
        ("qtd", "percentual"),
        FILTER_FIELDS,
        lambda frame: ce_macro_distribution_view(frame),
    ),
    "ce_monthly_trend_by_tema": ViewSpec(
        "ce_monthly_trend_by_tema",
        ("ano_mes", "macro_tema_label"),
        ("qtd",),
        FILTER_FIELDS,
        lambda frame: ce_monthly_trend_view(frame),
    ),
    "ce_cruzamento_erro_leitura": ViewSpec(
        "ce_cruzamento_erro_leitura",
        ("macro_tema_label",),
        ("qtd_com_erro_leitura", "qtd_total", "percentual"),
        FILTER_FIELDS,
        lambda frame: ce_cruzamento_view(frame),
    ),
    "governance_health": ViewSpec(
        "governance_health",
        ("label",),
        ("value", "status"),
        FILTER_FIELDS,
        lambda frame: governance_health_view(frame),
    ),
}


def _ce_scope_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    required = {"_source_region", "_data_type", "assunto", "ordem", "dt_ingresso"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()
    try:
        return prepare_reclamacoes_ce_frame(frame)
    except ValueError:
        return pd.DataFrame()


def ce_macro_distribution_view(frame: pd.DataFrame) -> pd.DataFrame:
    ce = _ce_scope_frame(frame)
    result = _ce_macro_tema_distribution(ce)
    if result.empty:
        return result
    out = result.copy()
    out["percentual"] = out["percentual"] / 100.0
    return out


def ce_monthly_trend_view(frame: pd.DataFrame) -> pd.DataFrame:
    ce = _ce_scope_frame(frame)
    return _ce_monthly_trend_by_tema(ce)


def ce_cruzamento_view(frame: pd.DataFrame) -> pd.DataFrame:
    ce = _ce_scope_frame(frame)
    erro = frame
    if "_data_type" in frame.columns:
        erro = frame.loc[frame["_data_type"] != "reclamacao_total"]
    result = _ce_cruzamento_com_erro_leitura(ce, erro)
    if result.empty:
        return result
    out = result.copy()
    out["percentual"] = out["percentual"] / 100.0
    return out


def governance_health_view(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["label", "value", "sub", "status"])
    total = int(len(frame))
    regioes = int(frame["regiao"].nunique()) if "regiao" in frame.columns else 0
    cobertura_causa = 0.0
    if "causa_canonica" in frame.columns:
        labeled = frame["causa_canonica"].fillna("").astype(str).str.strip()
        cobertura_causa = float(labeled.ne("").mean())
    cobertura_topico = 0.0
    if "topic_name" in frame.columns:
        topic = frame["topic_name"].fillna("").astype(str).str.strip()
        cobertura_topico = float(topic.ne("").mean())
    freshness_status = "ok"
    freshness_value = "—"
    freshness_sub = None
    if "dt_ingresso" in frame.columns:
        dt = pd.to_datetime(frame["dt_ingresso"], errors="coerce")
        max_dt = dt.max()
        if pd.notna(max_dt):
            days = int((pd.Timestamp.now().normalize() - max_dt.normalize()).days)
            freshness_value = f"{max_dt.date().isoformat()}"
            freshness_sub = f"há {days} dias"
            freshness_status = "ok" if days <= 7 else ("warn" if days <= 30 else "crit")

    rows = [
        {
            "label": "Volume carregado",
            "value": f"{total:,}".replace(",", "."),
            "sub": f"{regioes} regiões",
            "status": "ok" if total > 0 else "crit",
        },
        {
            "label": "Cobertura taxonomia",
            "value": f"{cobertura_causa * 100:.1f}%",
            "sub": "causa_canonica não-vazia",
            "status": _coverage_status(cobertura_causa, ok=0.85, warn=0.6),
        },
        {
            "label": "Cobertura tópicos ML",
            "value": f"{cobertura_topico * 100:.1f}%",
            "sub": "topic_name não-vazio",
            "status": _coverage_status(cobertura_topico, ok=0.8, warn=0.5),
        },
        {
            "label": "Frescor do dataset",
            "value": freshness_value,
            "sub": freshness_sub,
            "status": freshness_status,
        },
    ]
    return pd.DataFrame(rows)


def _coverage_status(value: float, *, ok: float, warn: float) -> str:
    if value >= ok:
        return "ok"
    if value >= warn:
        return "warn"
    return "crit"


def get_view(view_id: str) -> ViewSpec:
    try:
        return VIEW_REGISTRY[view_id]
    except KeyError as exc:
        known = ", ".join(sorted(VIEW_REGISTRY))
        raise KeyError(f"View desconhecida: {view_id}. Views disponiveis: {known}") from exc
