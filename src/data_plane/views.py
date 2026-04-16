"""Declarative BI/RAG view registry for the unified data plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

import pandas as pd

from src.viz.erro_leitura_dashboard_data import (
    category_breakdown,
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
    taxonomy_reference,
    topic_distribution,
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
    "topic_name",
    "status",
    "assunto",
    "start_date",
    "end_date",
)


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
}


def get_view(view_id: str) -> ViewSpec:
    try:
        return VIEW_REGISTRY[view_id]
    except KeyError as exc:
        known = ", ".join(sorted(VIEW_REGISTRY))
        raise KeyError(f"View desconhecida: {view_id}. Views disponiveis: {known}") from exc
