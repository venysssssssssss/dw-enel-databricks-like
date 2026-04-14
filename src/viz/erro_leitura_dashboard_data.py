"""Prepared analytical datasets for the erro de leitura dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pandas as pd

from src.ml.models.erro_leitura_classifier import (
    KEYWORD_TAXONOMY,
    TAXONOMY,
    KeywordErroLeituraClassifier,
    canonical_label,
    taxonomy_metadata,
)
from src.ml.models.erro_leitura_topic_model import _taxonomy_example

DEFAULT_SILVER_PATH = Path("data/silver/erro_leitura_normalizado.csv")
DEFAULT_TOPIC_ASSIGNMENTS_PATH = Path("data/model_registry/erro_leitura/topic_assignments.csv")
DEFAULT_TOPIC_TAXONOMY_PATH = Path("data/model_registry/erro_leitura/topic_taxonomy.json")
TRAINING_DATA_TYPES = {"erro_leitura", "base_n1_sp"}


@dataclass(frozen=True, slots=True)
class DashboardKpis:
    total_registros: int
    total_erros: int
    regioes: int
    topicos: int
    taxa_refaturamento: float
    taxa_rotulo_origem: float
    instalacoes_reincidentes: int


def load_dashboard_frame(
    *,
    silver_path: Path = DEFAULT_SILVER_PATH,
    topic_assignments_path: Path = DEFAULT_TOPIC_ASSIGNMENTS_PATH,
    topic_taxonomy_path: Path = DEFAULT_TOPIC_TAXONOMY_PATH,
    include_total: bool = False,
) -> pd.DataFrame:
    silver = pd.read_csv(silver_path, dtype=str, low_memory=False)
    assignments = _read_optional_csv(topic_assignments_path)
    taxonomy = _read_optional_json(topic_taxonomy_path)
    return prepare_dashboard_frame(
        silver,
        topic_assignments=assignments,
        topic_taxonomy=taxonomy,
        include_total=include_total,
    )


def prepare_dashboard_frame(
    silver: pd.DataFrame,
    *,
    topic_assignments: pd.DataFrame | None = None,
    topic_taxonomy: pd.DataFrame | None = None,
    include_total: bool = False,
) -> pd.DataFrame:
    required = {"ordem", "_source_region", "_data_type", "dt_ingresso"}
    missing = sorted(required.difference(silver.columns))
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes no dataset visual: {missing}")

    frame = silver.copy()
    if not include_total:
        frame = frame.loc[frame["_data_type"].isin(TRAINING_DATA_TYPES)].copy()

    frame["data_ingresso"] = pd.to_datetime(frame["dt_ingresso"], errors="coerce")
    frame["mes_ingresso"] = frame["data_ingresso"].dt.to_period("M").dt.to_timestamp()
    frame["regiao"] = frame["_source_region"].fillna("NAO_INFORMADA").astype(str)
    frame["tipo_origem"] = frame["_data_type"].fillna("NAO_INFORMADO").astype(str)
    frame["causa_canonica"] = _canonical_causes(frame)
    frame["flag_resolvido_com_refaturamento"] = _to_bool(
        frame.get("flag_resolvido_com_refaturamento", pd.Series(False, index=frame.index))
    )
    frame["has_causa_raiz_label"] = _to_bool(
        frame.get("has_causa_raiz_label", pd.Series(False, index=frame.index))
    )
    frame["instalacao_hash"] = frame.get(
        "instalacao",
        pd.Series("", index=frame.index),
    ).map(_hash_identifier)

    if topic_assignments is not None and not topic_assignments.empty:
        assignments = topic_assignments[["ordem", "topic_id"]].copy()
        assignments["ordem"] = assignments["ordem"].astype(str)
        assignments["topic_id"] = assignments["topic_id"].astype(str)
        frame = frame.merge(assignments, on="ordem", how="left")
    else:
        frame["topic_id"] = pd.NA

    if topic_taxonomy is not None and not topic_taxonomy.empty:
        taxonomy = _safe_topic_taxonomy(topic_taxonomy)
        frame = frame.merge(
            taxonomy[["topic_id", "topic_name", "topic_keywords"]],
            on="topic_id",
            how="left",
        )
    else:
        frame["topic_name"] = "sem_topico"
        frame["topic_keywords"] = ""

    frame["topic_name"] = frame["topic_name"].fillna("sem_topico")
    frame["topic_keywords"] = frame["topic_keywords"].fillna("")
    columns = [
        "ordem",
        "data_ingresso",
        "mes_ingresso",
        "regiao",
        "tipo_origem",
        "causa_canonica",
        "status",
        "assunto",
        "flag_resolvido_com_refaturamento",
        "has_causa_raiz_label",
        "instalacao_hash",
        "topic_id",
        "topic_name",
        "topic_keywords",
    ]
    available = [column for column in columns if column in frame.columns]
    return frame[available].reset_index(drop=True)


def compute_kpis(frame: pd.DataFrame) -> DashboardKpis:
    total = len(frame)
    refaturamento_rate = float(frame["flag_resolvido_com_refaturamento"].mean()) if total else 0.0
    label_rate = float(frame["has_causa_raiz_label"].mean()) if total else 0.0
    repeated_installations = (
        frame.loc[frame["instalacao_hash"].ne("")]
        .groupby("instalacao_hash", dropna=True)["ordem"]
        .nunique()
        .gt(1)
        .sum()
    )
    return DashboardKpis(
        total_registros=total,
        total_erros=int(frame.loc[frame["tipo_origem"].isin(TRAINING_DATA_TYPES)].shape[0]),
        regioes=int(frame["regiao"].nunique()) if total else 0,
        topicos=(
            int(frame.loc[frame["topic_name"].ne("sem_topico"), "topic_name"].nunique())
            if total
            else 0
        ),
        taxa_refaturamento=refaturamento_rate,
        taxa_rotulo_origem=label_rate,
        instalacoes_reincidentes=int(repeated_installations),
    )


def monthly_volume(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.dropna(subset=["mes_ingresso"])
        .groupby(["mes_ingresso", "regiao"], as_index=False)
        .agg(qtd_erros=("ordem", "nunique"))
        .sort_values(["mes_ingresso", "regiao"])
    )


def root_cause_distribution(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    grouped = (
        frame.groupby("causa_canonica", as_index=False)
        .agg(
            qtd_erros=("ordem", "nunique"),
            taxa_refaturamento=("flag_resolvido_com_refaturamento", "mean"),
        )
        .sort_values("qtd_erros", ascending=False)
        .head(limit)
    )
    total = max(int(grouped["qtd_erros"].sum()), 1)
    grouped["percentual"] = grouped["qtd_erros"] / total
    return grouped


def region_cause_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.pivot_table(
            index="causa_canonica",
            columns="regiao",
            values="ordem",
            aggfunc="nunique",
            fill_value=0,
        )
        .reset_index()
        .sort_values("causa_canonica")
    )


def topic_distribution(frame: pd.DataFrame, *, limit: int = 12) -> pd.DataFrame:
    grouped = (
        frame.groupby(["topic_name", "topic_keywords"], as_index=False)
        .agg(
            qtd_erros=("ordem", "nunique"),
            taxa_refaturamento=("flag_resolvido_com_refaturamento", "mean"),
        )
        .sort_values("qtd_erros", ascending=False)
        .head(limit)
    )
    return grouped


def refaturamento_by_cause(frame: pd.DataFrame, *, limit: int = 10) -> pd.DataFrame:
    return (
        frame.groupby("causa_canonica", as_index=False)
        .agg(
            qtd_erros=("ordem", "nunique"),
            taxa_refaturamento=("flag_resolvido_com_refaturamento", "mean"),
        )
        .query("qtd_erros > 0")
        .sort_values(["taxa_refaturamento", "qtd_erros"], ascending=[False, False])
        .head(limit)
    )


def radar_causes_by_region(frame: pd.DataFrame, *, top_n: int = 10) -> pd.DataFrame:
    """Formato long adequado a um radar chart (Plotly line_polar).

    Para cada regiao, retorna a share percentual de cada causa (top_n globais)
    sobre o total da regiao — permite comparar perfis CE vs SP em um unico grafico
    teia de aranha.
    """
    if frame.empty:
        return pd.DataFrame(columns=["regiao", "causa_canonica", "percentual", "qtd_erros"])

    counts = (
        frame.groupby(["regiao", "causa_canonica"], as_index=False)
        .agg(qtd_erros=("ordem", "nunique"))
    )
    top_causes = (
        counts.groupby("causa_canonica", as_index=False)["qtd_erros"]
        .sum()
        .sort_values("qtd_erros", ascending=False)
        .head(top_n)["causa_canonica"]
        .tolist()
    )
    if not top_causes:
        return pd.DataFrame(columns=["regiao", "causa_canonica", "percentual", "qtd_erros"])

    regioes = sorted(frame["regiao"].dropna().unique().tolist())
    grid = pd.MultiIndex.from_product(
        [regioes, top_causes], names=["regiao", "causa_canonica"]
    ).to_frame(index=False)
    merged = grid.merge(counts, on=["regiao", "causa_canonica"], how="left")
    merged["qtd_erros"] = merged["qtd_erros"].fillna(0).astype(int)
    totals = merged.groupby("regiao")["qtd_erros"].transform("sum").replace(0, 1)
    merged["percentual"] = merged["qtd_erros"] / totals
    return merged.sort_values(["regiao", "causa_canonica"]).reset_index(drop=True)


def category_breakdown(frame: pd.DataFrame) -> pd.DataFrame:
    """Agrupa causas pela `categoria` da taxonomia (processo, cadastro, etc)."""
    if frame.empty:
        return pd.DataFrame(columns=["categoria", "regiao", "qtd_erros", "percentual"])
    meta = taxonomy_metadata()[["classe", "categoria", "severidade"]]
    merged = frame.merge(meta, left_on="causa_canonica", right_on="classe", how="left")
    merged["categoria"] = merged["categoria"].fillna("nao_classificada")
    grouped = (
        merged.groupby(["categoria", "regiao"], as_index=False)
        .agg(qtd_erros=("ordem", "nunique"))
    )
    totals = grouped.groupby("regiao")["qtd_erros"].transform("sum").replace(0, 1)
    grouped["percentual"] = grouped["qtd_erros"] / totals
    return grouped.sort_values(["regiao", "qtd_erros"], ascending=[True, False])


def severity_heatmap(frame: pd.DataFrame) -> pd.DataFrame:
    """Matriz regiao x severidade com volume e taxa de refaturamento."""
    if frame.empty:
        return pd.DataFrame(columns=["regiao", "severidade", "qtd_erros", "taxa_refaturamento"])
    meta = taxonomy_metadata()[["classe", "severidade"]]
    merged = frame.merge(meta, left_on="causa_canonica", right_on="classe", how="left")
    merged["severidade"] = pd.Categorical(
        merged["severidade"].fillna("low"),
        categories=["critical", "high", "medium", "low"],
        ordered=True,
    )
    return (
        merged.groupby(["regiao", "severidade"], as_index=False, observed=True)
        .agg(
            qtd_erros=("ordem", "nunique"),
            taxa_refaturamento=("flag_resolvido_com_refaturamento", "mean"),
        )
        .sort_values(["regiao", "severidade"])
    )


def mis_executive_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """One-line-per-region summary para o MIS executivo (BI-ready)."""
    if frame.empty:
        return pd.DataFrame()
    meta = taxonomy_metadata()[["classe", "severidade", "peso_severidade"]]
    merged = frame.merge(meta, left_on="causa_canonica", right_on="classe", how="left")
    merged["peso_severidade"] = merged["peso_severidade"].fillna(1.0)

    def _aggregate(group: pd.DataFrame) -> pd.Series:
        total = int(group["ordem"].nunique())
        refat = float(group["flag_resolvido_com_refaturamento"].mean()) if total else 0.0
        label_cov = float(group["has_causa_raiz_label"].mean()) if total else 0.0
        top_cause = (
            group.groupby("causa_canonica")["ordem"].nunique().sort_values(ascending=False)
        )
        top1 = top_cause.index[0] if len(top_cause) else "n/d"
        top1_share = float(top_cause.iloc[0] / total) if total and len(top_cause) else 0.0
        reincidentes = (
            group.loc[group["instalacao_hash"].ne("")]
            .groupby("instalacao_hash")["ordem"]
            .nunique()
            .gt(1)
            .sum()
        )
        severity_score = float(group["peso_severidade"].mean()) if total else 0.0
        critical_share = float(group["severidade"].eq("critical").mean()) if total else 0.0
        return pd.Series(
            {
                "volume_total": total,
                "taxa_refaturamento": refat,
                "cobertura_rotulo": label_cov,
                "instalacoes_reincidentes": int(reincidentes),
                "causa_dominante": top1,
                "share_causa_dominante": top1_share,
                "severidade_media": round(severity_score, 2),
                "share_critico": critical_share,
            }
        )

    grouped = merged.groupby("regiao", group_keys=False).apply(_aggregate, include_groups=False)
    return grouped.reset_index() if isinstance(grouped, pd.DataFrame) else grouped.to_frame().T


def mis_monthly_mis(frame: pd.DataFrame) -> pd.DataFrame:
    """Serie mensal com MoM (% de variacao mes-a-mes) por regiao — alimenta o MIS."""
    if frame.empty:
        return pd.DataFrame(columns=["mes_ingresso", "regiao", "qtd_erros", "mom"])
    monthly = (
        frame.dropna(subset=["mes_ingresso"])
        .groupby(["mes_ingresso", "regiao"], as_index=False)
        .agg(qtd_erros=("ordem", "nunique"))
        .sort_values(["regiao", "mes_ingresso"])
    )
    monthly["mom"] = monthly.groupby("regiao")["qtd_erros"].pct_change().fillna(0.0)
    monthly["media_movel_3m"] = (
        monthly.groupby("regiao")["qtd_erros"]
        .transform(lambda series: series.rolling(3, min_periods=1).mean())
    )
    return monthly


def reincidence_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Perfil de reincidencia por regiao: quantas instalacoes caem em 1, 2, 3+ ordens."""
    if frame.empty:
        return pd.DataFrame(columns=["regiao", "faixa", "qtd_instalacoes"])
    df = frame.loc[frame["instalacao_hash"].ne("")]
    counts = df.groupby(["regiao", "instalacao_hash"], as_index=False).agg(
        qtd_ordens=("ordem", "nunique")
    )
    bins = [0, 1, 2, 4, 10, float("inf")]
    labels = ["1", "2", "3-4", "5-9", "10+"]
    counts["faixa"] = pd.cut(counts["qtd_ordens"], bins=bins, labels=labels, right=True)
    return (
        counts.groupby(["regiao", "faixa"], as_index=False, observed=True)
        .agg(qtd_instalacoes=("instalacao_hash", "nunique"))
        .sort_values(["regiao", "faixa"])
    )


def taxonomy_reference() -> pd.DataFrame:
    """Expoe a taxonomia v2 para a aba MIS (classes + descricoes + severidade)."""
    meta = taxonomy_metadata()
    meta = meta.rename(
        columns={
            "classe": "Causa canonica",
            "categoria": "Categoria",
            "severidade": "Severidade",
            "descricao": "Descricao",
            "n_keywords": "Nº termos",
            "peso_severidade": "Peso",
        }
    )
    return meta[["Causa canonica", "Categoria", "Severidade", "Peso", "Nº termos", "Descricao"]]


def safe_topic_taxonomy_for_display(topic_taxonomy: pd.DataFrame) -> pd.DataFrame:
    taxonomy = _safe_topic_taxonomy(topic_taxonomy)
    if "examples" in topic_taxonomy.columns:
        taxonomy["examples"] = topic_taxonomy["examples"].map(_safe_examples)
    return taxonomy


def _canonical_causes(frame: pd.DataFrame) -> pd.Series:
    labels = frame.get("causa_raiz", pd.Series(index=frame.index, dtype=object))
    canonical = labels.map(canonical_label)
    missing = canonical.isna()
    if missing.any():
        classifier = KeywordErroLeituraClassifier()
        texts = frame.get("texto_completo", pd.Series("", index=frame.index)).fillna("").astype(str)
        fallback = texts.map(lambda text: _keyword_label_or_indefinido(classifier, text))
        canonical.loc[missing] = fallback.loc[missing]
    return canonical.fillna("indefinido").astype(str)


def _keyword_label_or_indefinido(classifier: KeywordErroLeituraClassifier, text: str) -> str:
    """Usa classificador v2 (com threshold e ambiguidade). Retorna `indefinido`
    apenas quando o texto realmente nao tem sinal — reduz drasticamente o bucket
    generico em SP que antes caia em `outros`."""
    result = classifier.classify(text)
    return str(result["classe"])


def _to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.casefold().isin({"true", "1", "sim", "yes"})


def _safe_topic_taxonomy(topic_taxonomy: pd.DataFrame) -> pd.DataFrame:
    taxonomy = topic_taxonomy.copy()
    taxonomy["topic_id"] = taxonomy["topic_id"].astype(str)
    taxonomy["topic_name"] = taxonomy.get(
        "topic_name",
        pd.Series("sem_topico", index=taxonomy.index),
    ).astype(str)
    taxonomy["topic_keywords"] = taxonomy.get(
        "keywords",
        pd.Series("", index=taxonomy.index),
    ).map(_join_keywords)
    return taxonomy


def _safe_examples(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_taxonomy_example(item) for item in value[:3]]


def _join_keywords(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value[:8])
    if pd.isna(value):
        return ""
    return str(value)


def _hash_identifier(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text or text.casefold() == "nan":
        return ""
    return sha256(text.encode("utf-8")).hexdigest()[:12]


def _read_optional_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, dtype=str, low_memory=False)


def _read_optional_json(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_json(path)
