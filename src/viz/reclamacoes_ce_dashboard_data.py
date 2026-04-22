"""Analytical data layer for CE total complaints (reclamações totais).

Operates on the Silver layer rows where `_source_region == 'CE'` and
`_data_type == 'reclamacao_total'`. Uses the ENEL `assunto` field as the
authoritative label and collapses its ~120 values into 8 business macro-themes.
`causa_raiz` (when present) provides a second-level drill-down.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pandas as pd

from src.viz.cache import load_or_build_disk_cache, path_fingerprint

DEFAULT_SILVER_PATH = Path("data/silver/erro_leitura_normalizado.csv")
RECLAMACOES_CE_CACHE_VERSION = "s14-perf-v1"
RECLAMACOES_CE_COLUMNS = {
    "_source_region",
    "_data_type",
    "grupo",
    "ordem",
    "assunto",
    "instalacao",
    "dt_ingresso",
    "causa_raiz",
}

MACRO_TEMA_ORDER: tuple[str, ...] = (
    "refaturamento",
    "geracao_distribuida",
    "variacao_consumo",
    "media_estimativa",
    "ouvidoria_juridico",
    "religacao_multas",
    "entrega_fatura",
    "outros",
)

MACRO_TEMA_LABELS: dict[str, str] = {
    "refaturamento": "Refaturamento & Cobrança",
    "geracao_distribuida": "Geração Distribuída (GD)",
    "variacao_consumo": "Variação de Consumo",
    "media_estimativa": "Faturamento por Média/Estimativa",
    "ouvidoria_juridico": "Ouvidoria & Auditoria",
    "religacao_multas": "Religação & Multas",
    "entrega_fatura": "Entrega da Fatura",
    "outros": "Outros",
}

MACRO_TEMA_SEVERITY: dict[str, str] = {
    "refaturamento": "high",
    "geracao_distribuida": "high",
    "variacao_consumo": "medium",
    "media_estimativa": "high",
    "ouvidoria_juridico": "medium",
    "religacao_multas": "critical",
    "entrega_fatura": "medium",
    "outros": "low",
}


def _macro_tema_rules() -> list[tuple[str, tuple[str, ...]]]:
    """Ordered rules (first match wins). Tokens matched against uppercased assunto."""
    return [
        (
            "geracao_distribuida",
            (" GD", "GD ", "B2G", "RATEIO", "INJETADA", "MICRO GERA", "MINI GERA"),
        ),
        (
            "religacao_multas",
            (
                "AUTORELIG",
                "AUTO RELIG",
                "RELIGAC",
                "A REVELIA",
                "REVELIA",
                "MULTA",
                "TOI",
                "PERDAS",
                "CORTE",
            ),
        ),
        (
            "entrega_fatura",
            (
                "CONTA NÃO ENTREGUE",
                "CONTA NAO ENTREGUE",
                "FATURA NÃO ENTREGUE",
                "FATURA NAO ENTREGUE",
                "ENTREGA DE CONTA",
                "ENTREGA DE FATURA",
                "FATURA DIGITAL",
                "END POSTAL",
                "EMAIL",
            ),
        ),
        (
            "media_estimativa",
            (
                "POR MEDIA",
                "POR MÉDIA",
                "FATURAMENTO POR M",
                "ESTIMAD",
                "AUSENCIA DE FATURAMENTO",
                "AUSENCIA DE FATURA",
            ),
        ),
        (
            "variacao_consumo",
            (
                "VARIACAO",
                "VARIAÇÃO",
                "CONSUMO ATIPICO",
                "CONSUMO ATÍPICO",
                "DESCONHECE A UC",
                "CUSTO DE DISPONIBILIDADE",
            ),
        ),
        (
            "ouvidoria_juridico",
            (
                "OUV",
                "OUVIDORIA",
                "AUD",
                "AUDITORIA",
                "JURID",
                "PROCON",
                "ANEEL",
            ),
        ),
        (
            "refaturamento",
            (
                "REFAT",
                "REFATURAMENTO",
                "COBRANC",
                "COBRANÇ",
                "TARIFA",
                "ICMS",
                "FATURAMENTO",
                "CREDIT",
                "RESSARCIMEN",
                "ERRO DE LEITURA",
                "ITENS FINANCEIROS",
                "INCLUSAO DE VALORES",
                "PARCELAMENTO",
                "LIGAÇAO PROVISORIA",
                "LIGACAO PROVISORIA",
            ),
        ),
    ]


def classify_macro_tema(assunto: str | float | None) -> str:
    if not isinstance(assunto, str) or not assunto.strip():
        return "outros"
    haystack = assunto.upper()
    for tema, tokens in _macro_tema_rules():
        if any(token in haystack for token in tokens):
            return tema
    return "outros"


@dataclass(frozen=True, slots=True)
class ReclamacoesKpis:
    total_reclamacoes: int
    unique_instalacoes: int
    instalacoes_reincidentes: int
    share_grupo_b: float
    taxa_rotulo_causa_raiz: float
    tema_dominante: str
    share_tema_dominante: float
    assuntos_distintos: int
    meses_cobertos: int


def load_reclamacoes_ce(
    silver_path: Path = DEFAULT_SILVER_PATH,
) -> pd.DataFrame:
    signature = sha256(
        f"{path_fingerprint(silver_path)}|{RECLAMACOES_CE_CACHE_VERSION}".encode()
    ).hexdigest()
    return load_or_build_disk_cache(
        Path(".streamlit/cache"),
        "reclamacoes_ce_frame",
        signature,
        lambda: _build_reclamacoes_ce_frame(silver_path),
    )


def _build_reclamacoes_ce_frame(silver_path: Path) -> pd.DataFrame:
    silver = pd.read_csv(
        silver_path,
        dtype=str,
        low_memory=False,
        usecols=lambda column: column in RECLAMACOES_CE_COLUMNS,
    )
    return prepare_reclamacoes_ce_frame(silver)


def prepare_reclamacoes_ce_frame(silver: pd.DataFrame) -> pd.DataFrame:
    required = {"_source_region", "_data_type", "assunto", "ordem", "dt_ingresso"}
    missing = required - set(silver.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    frame = silver.loc[
        (silver["_source_region"] == "CE") & (silver["_data_type"] == "reclamacao_total")
    ].copy()
    if frame.empty:
        return frame

    frame["dt_ingresso"] = pd.to_datetime(frame["dt_ingresso"], errors="coerce")
    frame["ano_mes"] = frame["dt_ingresso"].dt.to_period("M").astype(str)
    frame["assunto_clean"] = frame["assunto"].fillna("(sem assunto)").str.strip().str.upper()
    frame["macro_tema"] = frame["assunto_clean"].map(classify_macro_tema)
    frame["macro_tema_label"] = (
        frame["macro_tema"].map(MACRO_TEMA_LABELS).fillna(MACRO_TEMA_LABELS["outros"])
    )
    frame["severidade"] = frame["macro_tema"].map(MACRO_TEMA_SEVERITY).fillna("low")
    frame["grupo_norm"] = frame["grupo"].fillna("").str.strip().str.upper().replace({"": "ND"})
    frame["causa_raiz_clean"] = frame["causa_raiz"].fillna("").str.strip()
    frame["tem_causa_raiz"] = frame["causa_raiz_clean"].str.len().gt(0)
    frame["instalacao_clean"] = frame["instalacao"].fillna("").astype(str).str.strip()
    frame["instalacao_hash"] = frame["instalacao_clean"].map(_hash_installation)
    return frame


def compute_kpis(frame: pd.DataFrame) -> ReclamacoesKpis:
    if frame.empty:
        return ReclamacoesKpis(0, 0, 0, 0.0, 0.0, "—", 0.0, 0, 0)
    tema_counts = frame["macro_tema_label"].value_counts()
    tema_dominante = str(tema_counts.index[0])
    share_dominante = float(tema_counts.iloc[0] / len(frame))
    instalacao_counts = frame.loc[
        frame["instalacao_clean"].ne(""),
        "instalacao_hash",
    ].value_counts()
    reincidentes = int((instalacao_counts >= 2).sum())
    unique_inst = int((instalacao_counts > 0).sum())
    meses = int(frame["ano_mes"].nunique())
    return ReclamacoesKpis(
        total_reclamacoes=int(len(frame)),
        unique_instalacoes=unique_inst,
        instalacoes_reincidentes=reincidentes,
        share_grupo_b=float((frame["grupo_norm"] == "GB").mean()),
        taxa_rotulo_causa_raiz=float(frame["tem_causa_raiz"].mean()),
        tema_dominante=tema_dominante,
        share_tema_dominante=share_dominante,
        assuntos_distintos=int(frame["assunto_clean"].nunique()),
        meses_cobertos=meses,
    )


def macro_tema_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["macro_tema", "macro_tema_label", "qtd", "percentual"])
    counts = (
        frame.groupby(["macro_tema", "macro_tema_label"], dropna=False)
        .size()
        .reset_index(name="qtd")
    )
    counts["percentual"] = counts["qtd"] / counts["qtd"].sum() * 100
    counts["ordem"] = (
        counts["macro_tema"].map({t: i for i, t in enumerate(MACRO_TEMA_ORDER)}).fillna(99)
    )
    return counts.sort_values("qtd", ascending=False).drop(columns="ordem").reset_index(drop=True)


def assunto_pareto(frame: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["assunto", "qtd", "percentual", "acumulado_pct"])
    counts = frame["assunto_clean"].value_counts().head(top_n).reset_index()
    counts.columns = ["assunto", "qtd"]
    total = int(frame.shape[0])
    counts["percentual"] = counts["qtd"] / total * 100
    counts["acumulado_pct"] = counts["percentual"].cumsum()
    return counts


def causa_raiz_drill(
    frame: pd.DataFrame,
    macro_tema: str | None = None,
    top_n: int = 15,
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["causa_raiz", "qtd", "percentual"])
    subset = frame.loc[frame["tem_causa_raiz"]].copy()
    if macro_tema:
        subset = subset.loc[subset["macro_tema"] == macro_tema]
    if subset.empty:
        return pd.DataFrame(columns=["causa_raiz", "qtd", "percentual"])
    counts = subset["causa_raiz_clean"].value_counts().head(top_n).reset_index()
    counts.columns = ["causa_raiz", "qtd"]
    counts["percentual"] = counts["qtd"] / len(subset) * 100
    return counts


def monthly_trend_by_tema(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["ano_mes", "macro_tema_label", "qtd", "mom", "media_movel_3m"])
    pivot = (
        frame.groupby(["ano_mes", "macro_tema_label"], dropna=False)
        .size()
        .reset_index(name="qtd")
        .sort_values(["macro_tema_label", "ano_mes"])
    )
    pivot["mom"] = pivot.groupby("macro_tema_label")["qtd"].pct_change()
    pivot["media_movel_3m"] = (
        pivot.groupby("macro_tema_label")["qtd"].transform(
            lambda s: s.rolling(3, min_periods=1).mean()
        )
    )
    return pivot.reset_index(drop=True)


def heatmap_tema_x_mes(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    matrix = (
        frame.pivot_table(
            index="macro_tema_label",
            columns="ano_mes",
            values="ordem",
            aggfunc="count",
            fill_value=0,
        )
        .sort_index(axis=1)
    )
    order = [MACRO_TEMA_LABELS[t] for t in MACRO_TEMA_ORDER if MACRO_TEMA_LABELS[t] in matrix.index]
    return matrix.loc[order]


def top_instalacoes_reincidentes(frame: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=["instalacao_hash", "qtd_reclamacoes", "temas_distintos", "ultimo_ingresso"]
        )
    subset = frame.loc[frame["instalacao_clean"].ne("")]
    grouped = (
        subset.groupby("instalacao_hash")
        .agg(
            qtd_reclamacoes=("ordem", "count"),
            temas_distintos=("macro_tema", "nunique"),
            ultimo_ingresso=("dt_ingresso", "max"),
        )
        .reset_index()
        .sort_values("qtd_reclamacoes", ascending=False)
        .head(top_n)
    )
    return grouped


def radar_tema_por_grupo(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["grupo", "macro_tema_label", "qtd", "percentual"])
    counts = (
        frame.groupby(["grupo_norm", "macro_tema_label"], dropna=False)
        .size()
        .reset_index(name="qtd")
    )
    counts = counts.rename(columns={"grupo_norm": "grupo"})
    totals = counts.groupby("grupo")["qtd"].transform("sum").replace(0, 1)
    counts["percentual"] = counts["qtd"] / totals * 100
    grid_grupos = counts["grupo"].drop_duplicates().tolist()
    grid_temas = [MACRO_TEMA_LABELS[t] for t in MACRO_TEMA_ORDER]
    idx = pd.MultiIndex.from_product([grid_grupos, grid_temas], names=["grupo", "macro_tema_label"])
    return (
        counts.set_index(["grupo", "macro_tema_label"]).reindex(idx, fill_value=0).reset_index()
    )


def cruzamento_com_erro_leitura(
    reclamacoes_ce: pd.DataFrame,
    erro_leitura_frame: pd.DataFrame,
) -> pd.DataFrame:
    """Identifies installations that appear in BOTH datasets — candidates for
    reading-error as the root cause of broader complaints."""
    empty_out = pd.DataFrame(
        columns=["macro_tema_label", "qtd_com_erro_leitura", "qtd_total", "percentual"]
    )
    if reclamacoes_ce.empty or erro_leitura_frame.empty:
        return empty_out
    if "instalacao_hash" not in erro_leitura_frame.columns:
        return empty_out
    subset = erro_leitura_frame
    if "_source_region" in erro_leitura_frame.columns:
        subset = erro_leitura_frame.loc[erro_leitura_frame["_source_region"] == "CE"]
    erro_inst = subset["instalacao_hash"].dropna().unique()
    erro_set = {h for h in erro_inst if h}
    if not erro_set:
        return empty_out
    rec = reclamacoes_ce.copy()
    rec["tem_erro_leitura"] = rec["instalacao_hash"].isin(erro_set)
    grouped = (
        rec.groupby("macro_tema_label")
        .agg(
            qtd_com_erro_leitura=("tem_erro_leitura", "sum"),
            qtd_total=("tem_erro_leitura", "count"),
        )
        .reset_index()
    )
    grouped["percentual"] = grouped["qtd_com_erro_leitura"] / grouped["qtd_total"] * 100
    return grouped.sort_values("qtd_com_erro_leitura", ascending=False).reset_index(drop=True)


def reincidence_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["bucket", "instalacoes"])
    subset = frame.loc[frame["instalacao_clean"].ne("")]
    if subset.empty:
        return pd.DataFrame(columns=["bucket", "instalacoes"])
    counts = subset["instalacao_hash"].value_counts()
    buckets = pd.cut(
        counts.values,
        bins=[0, 1, 2, 4, 9, 10_000],
        labels=["1", "2", "3-4", "5-9", "10+"],
        include_lowest=True,
    )
    out = pd.Series(buckets).value_counts().reindex(["1", "2", "3-4", "5-9", "10+"], fill_value=0)
    return pd.DataFrame({"bucket": out.index.astype(str), "instalacoes": out.values})


def executive_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    kpis = compute_kpis(frame)
    data = {
        "Métrica": [
            "Volume total",
            "Instalações únicas",
            "Instalações reincidentes (≥2)",
            "% Grupo B",
            "Cobertura de causa-raiz",
            "Tema dominante",
            "Share do tema dominante",
            "Assuntos distintos",
            "Meses cobertos",
        ],
        "Valor": [
            f"{kpis.total_reclamacoes:,}".replace(",", "."),
            f"{kpis.unique_instalacoes:,}".replace(",", "."),
            f"{kpis.instalacoes_reincidentes:,}".replace(",", "."),
            f"{kpis.share_grupo_b * 100:.1f}%",
            f"{kpis.taxa_rotulo_causa_raiz * 100:.1f}%",
            kpis.tema_dominante,
            f"{kpis.share_tema_dominante * 100:.1f}%",
            str(kpis.assuntos_distintos),
            str(kpis.meses_cobertos),
        ],
    }
    return pd.DataFrame(data)


def _hash_installation(value: str) -> str:
    if not value:
        return ""
    return sha256(value.encode("utf-8")).hexdigest()[:12]
