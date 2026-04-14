"""Prepared analytical datasets for the erro de leitura dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pandas as pd

from src.ml.models.erro_leitura_classifier import (
    KEYWORD_TAXONOMY,
    KeywordErroLeituraClassifier,
    canonical_label,
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
        fallback = texts.map(lambda text: _keyword_label_or_outros(classifier, text))
        canonical.loc[missing] = fallback.loc[missing]
    return canonical.fillna("outros").astype(str)


def _keyword_label_or_outros(classifier: KeywordErroLeituraClassifier, text: str) -> str:
    result = classifier.classify(text)
    minimum_signal = (1.0 / max(len(KEYWORD_TAXONOMY), 1)) + 0.001
    if float(result["probabilidade"]) <= minimum_signal:
        return "outros"
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
