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
                "cobertura_fatura_pct": float(sub.get("perfil_fatura_disponivel", pd.Series(False)).mean()),
                "cobertura_medidor_pct": float(sub.get("perfil_medidor_disponivel", pd.Series(False)).mean()),
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
        label = peak_month.strftime("%Y-%m") if hasattr(peak_month, "strftime") else str(peak_month)[:7]
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
        out.sort_values(["taxa_reincidencia", "qtd_instalacoes_reincidentes"], ascending=[False, False])
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
}


def get_view(view_id: str) -> ViewSpec:
    try:
        return VIEW_REGISTRY[view_id]
    except KeyError as exc:
        known = ", ".join(sorted(VIEW_REGISTRY))
        raise KeyError(f"View desconhecida: {view_id}. Views disponiveis: {known}") from exc
