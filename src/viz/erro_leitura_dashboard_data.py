"""Prepared analytical datasets for the erro de leitura dashboard."""

from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pandas as pd

from src.data_plane.enrichment import apply_enrichment
from src.ml.models.erro_leitura_classifier import (
    KeywordErroLeituraClassifier,
    canonical_label,
    normalize_text,
    taxonomy_metadata,
)

DEFAULT_SILVER_PATH = Path("data/silver/erro_leitura_normalizado.csv")
DEFAULT_TOPIC_ASSIGNMENTS_PATH = Path("data/model_registry/erro_leitura/topic_assignments.csv")
DEFAULT_TOPIC_TAXONOMY_PATH = Path("data/model_registry/erro_leitura/topic_taxonomy.json")
DEFAULT_TOPIC_TO_CANONICAL_PATH = Path("data/model_registry/erro_leitura/topic_to_canonical.csv")
DEFAULT_MEDIDOR_SP_PATH = Path("DESCRICOES_ENEL/medidor_20260417_20260416T090000.csv")
DEFAULT_FATURA_SP_PATH = Path("DESCRICOES_ENEL/DADOS_FATURA_SP_ORDENS001.XLSX")
DEFAULT_DESCRICOES_CLUSTER_PATH = Path("DESCRICOES_ENEL/erro_leitura_clusterizado.csv")
TRAINING_DATA_TYPES = {"erro_leitura", "base_n1_sp"}
KEYWORD_LABEL_CACHE_VERSION = "keyword-v3"
MAX_TAXONOMY_EXAMPLE_CHARS = 420
DASHBOARD_SILVER_COLUMNS = {
    "ordem",
    "_source_region",
    "_data_type",
    "dt_ingresso",
    "causa_raiz",
    "texto_completo",
    "flag_resolvido_com_refaturamento",
    "has_causa_raiz_label",
    "instalacao",
    "status",
    "assunto",
    "grupo",
    "observacao_ordem",
    "devolutiva",
    "causa_canonica_v3",
    "causa_canonica_confidence",
}


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
    from src.data_plane import DataStore

    return DataStore(
        silver_path=silver_path,
        topic_assignments_path=topic_assignments_path,
        topic_taxonomy_path=topic_taxonomy_path,
    ).load_silver(include_total=include_total)


def _build_dashboard_frame(
    *,
    silver_path: Path,
    topic_assignments_path: Path,
    topic_taxonomy_path: Path,
    include_total: bool,
) -> pd.DataFrame:
    if include_total:
        return _build_include_total_dashboard_frame(
            silver_path=silver_path,
            topic_assignments_path=topic_assignments_path,
            topic_taxonomy_path=topic_taxonomy_path,
        )

    silver = pd.read_csv(
        silver_path,
        dtype=str,
        low_memory=False,
        usecols=lambda column: column in DASHBOARD_SILVER_COLUMNS,
    )
    assignments = _read_optional_csv(topic_assignments_path)
    taxonomy = _read_optional_json(topic_taxonomy_path)
    topic_to_canonical = _read_optional_csv(DEFAULT_TOPIC_TO_CANONICAL_PATH)
    return prepare_dashboard_frame(
        silver,
        topic_assignments=assignments,
        topic_taxonomy=taxonomy,
        topic_to_canonical=topic_to_canonical,
        include_total=include_total,
    )


def _build_include_total_dashboard_frame(
    *,
    silver_path: Path,
    topic_assignments_path: Path,
    topic_taxonomy_path: Path,
) -> pd.DataFrame:
    training_frame = load_dashboard_frame(
        silver_path=silver_path,
        topic_assignments_path=topic_assignments_path,
        topic_taxonomy_path=topic_taxonomy_path,
        include_total=False,
    )
    silver = pd.read_csv(
        silver_path,
        dtype=str,
        low_memory=False,
        usecols=lambda column: column in DASHBOARD_SILVER_COLUMNS,
    )
    total_silver = silver.loc[~silver["_data_type"].isin(TRAINING_DATA_TYPES)].copy()
    if total_silver.empty:
        return training_frame
    total_frame = prepare_dashboard_frame(
        total_silver,
        topic_assignments=None,
        topic_taxonomy=None,
        topic_to_canonical=_read_optional_csv(DEFAULT_TOPIC_TO_CANONICAL_PATH),
        include_total=True,
    )
    return pd.concat([training_frame, total_frame], ignore_index=True)


def prepare_dashboard_frame(
    silver: pd.DataFrame,
    *,
    topic_assignments: pd.DataFrame | None = None,
    topic_taxonomy: pd.DataFrame | None = None,
    topic_to_canonical: pd.DataFrame | None = None,
    medidor_profile: pd.DataFrame | None = None,
    fatura_profile: pd.DataFrame | None = None,
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
    canonical = _canonical_cause_frame(frame)
    frame["causa_canonica"] = canonical["causa_canonica"]
    frame["causa_canonica_confidence"] = canonical["causa_canonica_confidence"]
    frame["flag_resolvido_com_refaturamento"] = _to_bool(
        frame.get("flag_resolvido_com_refaturamento", pd.Series(False, index=frame.index))
    )
    frame["has_causa_raiz_label"] = _to_bool(
        frame.get("has_causa_raiz_label", pd.Series(False, index=frame.index))
    )
    frame = _attach_procedencia_real(frame)
    frame["instalacao"] = frame.get(
        "instalacao",
        pd.Series("", index=frame.index),
    ).fillna("").astype(str)
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

    frame = _apply_topic_to_canonical(frame, topic_to_canonical)

    frame = apply_enrichment(
        frame,
        medidor_profile=medidor_profile,
        fatura_profile=fatura_profile,
    )

    frame["topic_name"] = frame["topic_name"].fillna("sem_topico")
    frame["topic_keywords"] = frame["topic_keywords"].fillna("")
    columns = [
        "ordem",
        "data_ingresso",
        "mes_ingresso",
        "regiao",
        "tipo_origem",
        "causa_canonica",
        "causa_canonica_confidence",
        "status",
        "assunto",
        "grupo",
        "instalacao",
        "texto_completo",
        "observacao_ordem",
        "devolutiva",
        "flag_resolvido_com_refaturamento",
        "procedente_real",
        "procedencia_real",
        "procedencia_known",
        "has_causa_raiz_label",
        "instalacao_hash",
        "tipo_medidor_dominante",
        "instalacao_multi_tipo",
        "equipamentos_unicos",
        "tipos_distintos",
        "valor_fatura_reclamada_medio",
        "valor_fatura_reclamada_max",
        "dias_emissao_ate_reclamacao_medio",
        "dias_vencimento_ate_reclamacao_medio",
        "fat_reclamada_top",
        "qtd_faturas_reclamadas",
        "perfil_fatura_disponivel",
        "perfil_medidor_disponivel",
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


_SEVERIDADE_ALIAS = {
    "alta": "high",
    "high": "high",
    "critica": "critical",
    "critical": "critical",
    "media": "medium",
    "medium": "medium",
    "baixa": "low",
    "low": "low",
}
_CONFIDENCE_ORDER = {"indefinido": 0, "low": 1, "high": 2}


_PROCEDENCIA_CACHE: dict[str, pd.DataFrame] = {}


def _load_procedencia_lookup(
    path: Path = DEFAULT_DESCRICOES_CLUSTER_PATH,
) -> pd.DataFrame:
    """Load NOTA RL → procedência ground truth from clusterized CSV.

    Cached in-process. Returns DataFrame with columns
    [ordem, procedencia_real, procedente_real_flag].
    """
    key = str(path)
    cached = _PROCEDENCIA_CACHE.get(key)
    if cached is not None:
        return cached
    cols = ["ordem", "procedencia_real", "procedente_real_flag"]
    if not Path(path).exists():
        _PROCEDENCIA_CACHE[key] = pd.DataFrame(columns=cols)
        return _PROCEDENCIA_CACHE[key]
    csv = pd.read_csv(path, sep=";", encoding="utf-8-sig", low_memory=False)
    csv.columns = [str(c).strip() for c in csv.columns]
    if "NOTA RL" not in csv.columns or "Procedencia" not in csv.columns:
        _PROCEDENCIA_CACHE[key] = pd.DataFrame(columns=cols)
        return _PROCEDENCIA_CACHE[key]
    proc_norm = csv["Procedencia"].fillna("").astype(str).str.strip().str.upper()
    label = proc_norm.where(
        proc_norm.isin(["PROCEDENTE", "IMPROCEDENTE"]),
        other="NAO_INFORMADA",
    )
    out = pd.DataFrame(
        {
            "ordem": csv["NOTA RL"].astype(str).str.strip(),
            "procedencia_real": label.values,
            "procedente_real_flag": label.eq("PROCEDENTE").values,
        }
    )
    out = out.drop_duplicates(subset=["ordem"], keep="last").reset_index(drop=True)
    _PROCEDENCIA_CACHE[key] = out
    return out


def _attach_procedencia_real(frame: pd.DataFrame) -> pd.DataFrame:
    """Merge ground-truth procedência (PROCEDENTE/IMPROCEDENTE) onto rows.

    Adds:
      - `procedencia_real`: PROCEDENTE | IMPROCEDENTE | NAO_INFORMADA.
      - `procedente_real`: bool — True only when CSV says PROCEDENTE.
      - `procedencia_known`: True when CSV had explicit label.
    Falls back to `flag_resolvido_com_refaturamento` only for the boolean
    when no CSV label exists; the textual label stays NAO_INFORMADA in
    that case so callers can distinguish "missing" from "improcedente".
    """
    lookup = _load_procedencia_lookup()
    if "ordem" not in frame.columns or lookup.empty:
        frame["procedencia_real"] = "NAO_INFORMADA"
        frame["procedente_real"] = frame["flag_resolvido_com_refaturamento"].astype(bool)
        frame["procedencia_known"] = False
        return frame
    work = frame.copy()
    work["ordem"] = work["ordem"].astype(str).str.strip()
    merged = work.merge(lookup, on="ordem", how="left")
    label = merged["procedencia_real"].fillna("NAO_INFORMADA").astype(str)
    flag = merged["procedente_real_flag"].astype("boolean")
    known = label.isin(["PROCEDENTE", "IMPROCEDENTE"])
    fallback = merged["flag_resolvido_com_refaturamento"].astype(bool)
    merged["procedencia_real"] = label.values
    merged["procedente_real"] = flag.fillna(False).astype(bool) | (~known & fallback)
    merged["procedencia_known"] = known.values
    merged.drop(columns=["procedente_real_flag"], inplace=True, errors="ignore")
    return merged


def _attach_severidade(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    meta = taxonomy_metadata()[["classe", "categoria", "severidade", "peso_severidade"]]
    merged = frame.merge(meta, left_on="causa_canonica", right_on="classe", how="left")
    merged["severidade"] = merged["severidade"].fillna("low")
    merged["categoria"] = merged["categoria"].fillna("nao_classificada")
    merged["peso_severidade"] = merged["peso_severidade"].fillna(1.0)
    return merged


def _resolve_severidades(severidade: str | tuple[str, ...] | list[str]) -> list[str]:
    if isinstance(severidade, (tuple, list)):
        sevs = [str(s).lower() for s in severidade]
    else:
        sevs = [str(severidade or "").lower()]
    if any(s in {"demais", "outras", "media_baixa"} for s in sevs):
        return ["medium", "low"]
    return [_SEVERIDADE_ALIAS.get(s, s) for s in sevs]


def _filter_sp_severidade(
    frame: pd.DataFrame,
    severidade: str | tuple[str, ...] | list[str],
    *,
    min_confidence: str = "high",
) -> pd.DataFrame:
    sev_keys = _resolve_severidades(severidade)
    df = _attach_severidade(frame)
    if df.empty:
        return df
    if "regiao" in df.columns:
        df = df.loc[df["regiao"].astype(str).str.upper().eq("SP")]
    df = df.loc[df["severidade"].isin(sev_keys)]
    df = _filter_min_confidence(df, min_confidence=min_confidence)
    return df


def _filter_min_confidence(frame: pd.DataFrame, *, min_confidence: str = "high") -> pd.DataFrame:
    if frame.empty or "causa_canonica_confidence" not in frame.columns:
        return frame
    key = str(min_confidence or "").casefold()
    if key in {"", "all", "todos", "any"}:
        return frame
    min_rank = _CONFIDENCE_ORDER.get(key, _CONFIDENCE_ORDER["high"])
    ranks = (
        frame["causa_canonica_confidence"]
        .fillna("indefinido")
        .astype(str)
        .str.casefold()
        .map(_CONFIDENCE_ORDER)
        .fillna(0)
    )
    return frame.loc[ranks.ge(min_rank)].copy()


def classifier_coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """Cobertura do classificador v3 por regiao e bucket de confianca."""
    cols = [
        "regiao",
        "causa_canonica_confidence",
        "qtd_ordens",
        "percentual",
        "indefinidos",
        "indefinido_pct",
    ]
    if frame.empty or "ordem" not in frame.columns:
        return pd.DataFrame(columns=cols)
    work = frame.copy()
    if "regiao" not in work.columns:
        work["regiao"] = "NAO_INFORMADA"
    if "causa_canonica" not in work.columns:
        work["causa_canonica"] = "indefinido"
    if "causa_canonica_confidence" not in work.columns:
        work["causa_canonica_confidence"] = "high"
    work["causa_canonica_confidence"] = (
        work["causa_canonica_confidence"]
        .fillna("indefinido")
        .astype(str)
        .where(lambda s: s.isin(["high", "low", "indefinido"]), "indefinido")
    )
    grouped = (
        work.groupby(["regiao", "causa_canonica_confidence"], as_index=False)
        .agg(qtd_ordens=("ordem", "nunique"))
        .sort_values(["regiao", "causa_canonica_confidence"])
    )
    totals = work.groupby("regiao")["ordem"].nunique().rename("_total")
    indef = (
        work.loc[work["causa_canonica"].astype(str).eq("indefinido")]
        .groupby("regiao")["ordem"]
        .nunique()
        .rename("indefinidos")
    )
    grouped = grouped.merge(totals, on="regiao", how="left").merge(indef, on="regiao", how="left")
    grouped["indefinidos"] = grouped["indefinidos"].fillna(0).astype(int)
    grouped["percentual"] = grouped["qtd_ordens"] / grouped["_total"].replace(0, 1)
    grouped["indefinido_pct"] = grouped["indefinidos"] / grouped["_total"].replace(0, 1)
    return grouped[cols]


def classifier_indefinido_tokens(frame: pd.DataFrame, *, limit: int = 20) -> pd.DataFrame:
    """Tokens de apoio para auditoria dos registros ainda indefinidos, sem expor texto cru."""
    cols = ["token", "qtd_ocorrencias"]
    if frame.empty:
        return pd.DataFrame(columns=cols)
    if "causa_canonica" not in frame.columns:
        return pd.DataFrame(columns=cols)
    sub = frame.loc[frame["causa_canonica"].fillna("").astype(str).eq("indefinido")].copy()
    if sub.empty:
        return pd.DataFrame(columns=cols)
    parts: list[pd.Series] = []
    for column in ("topic_keywords", "assunto"):
        if column in sub.columns:
            parts.append(sub[column].fillna("").astype(str))
    if not parts:
        return pd.DataFrame(columns=cols)
    text = pd.concat(parts, ignore_index=True).map(normalize_text)
    stopwords = {
        "a",
        "as",
        "com",
        "da",
        "de",
        "do",
        "e",
        "em",
        "na",
        "no",
        "o",
        "os",
        "para",
        "por",
    }
    tokens: list[str] = []
    for value in text:
        tokens.extend(
            token
            for token in re.findall(r"\b[a-z0-9_]{3,}\b", value)
            if token not in stopwords
        )
    if not tokens:
        return pd.DataFrame(columns=cols)
    return (
        pd.Series(tokens)
        .value_counts()
        .head(limit)
        .rename_axis("token")
        .reset_index(name="qtd_ocorrencias")
    )


def sp_severidade_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    """Severity distribution for SP using the same filters as per-route overviews.

    Returns one row per severity bucket (critical/high/medium/low) with
    `qtd_erros`, `procedentes`, `improcedentes`, `pct` so the MIS Executivo
    donut matches the totals reported by sp_severidade_*_overview.
    """
    cols = ["severidade", "qtd_erros", "procedentes", "improcedentes", "pct"]
    out_rows: list[dict[str, object]] = []
    grand_total = 0
    by_sev: dict[str, dict[str, int]] = {}
    for sev in ("critical", "high", "medium", "low"):
        df = _filter_sp_severidade(frame, sev)
        if df.empty:
            by_sev[sev] = {"qtd_erros": 0, "procedentes": 0, "improcedentes": 0}
            continue
        proc_col = "procedente_real" if "procedente_real" in df.columns else "flag_resolvido_com_refaturamento"
        proc_by_order = (
            df.assign(_proc=df[proc_col].fillna(False).astype(bool))
            .groupby("ordem")["_proc"]
            .any()
        )
        total = int(proc_by_order.shape[0])
        proc = int(proc_by_order.sum())
        by_sev[sev] = {
            "qtd_erros": total,
            "procedentes": proc,
            "improcedentes": max(0, total - proc),
        }
        grand_total += total
    for sev in ("critical", "high", "medium", "low"):
        d = by_sev[sev]
        out_rows.append(
            {
                "severidade": sev,
                "qtd_erros": d["qtd_erros"],
                "procedentes": d["procedentes"],
                "improcedentes": d["improcedentes"],
                "pct": round(d["qtd_erros"] / grand_total, 4) if grand_total else 0.0,
            }
        )
    return pd.DataFrame(out_rows, columns=cols)


def sp_severidade_overview(frame: pd.DataFrame, *, severidade: str = "high") -> pd.DataFrame:
    """KPIs para a página de Severidade (SP): totais, procedência, reincidência e valor."""
    columns = [
        "total",
        "procedentes",
        "improcedentes",
        "pct_procedentes",
        "reincidentes_clientes",
        "valor_medio_fatura",
        "categorias_count",
        "top3_share",
        "delta_trimestre",
    ]
    df = _filter_sp_severidade(frame, severidade)
    if df.empty:
        return pd.DataFrame([{col: 0 for col in columns}])

    total = int(df["ordem"].nunique())
    proc_col = "procedente_real" if "procedente_real" in df.columns else "flag_resolvido_com_refaturamento"
    proc_series = df[proc_col].fillna(False).astype(bool)
    # Conta por ordem distinta (caso uma ordem tenha múltiplas linhas).
    proc_by_order = df.assign(_proc=proc_series).groupby("ordem")["_proc"].any()
    procedentes = int(proc_by_order.sum())
    improcedentes = max(0, total - procedentes)
    pct_proc = (procedentes / total) if total else 0.0

    reinc_series = (
        df.loc[df["instalacao_hash"].ne("")]
        .groupby("instalacao_hash")["ordem"]
        .nunique()
    )
    reincidentes = int(reinc_series.gt(1).sum())

    valor_col = (
        "valor_fatura_reclamada_medio"
        if "valor_fatura_reclamada_medio" in df.columns
        else None
    )
    valor_medio = (
        float(df[valor_col].dropna().mean()) if valor_col and df[valor_col].notna().any() else 0.0
    )

    cat_group = df.groupby("categoria")["ordem"].nunique().sort_values(ascending=False)
    categorias_count = int((cat_group > 0).sum())
    top3 = cat_group.head(3).sum()
    top3_share = float(top3 / total) if total else 0.0

    delta_tri = 0.0
    if "mes_ingresso" in df.columns and df["mes_ingresso"].notna().any():
        monthly = (
            df.dropna(subset=["mes_ingresso"])
            .groupby("mes_ingresso")["ordem"]
            .nunique()
            .sort_index()
        )
        if len(monthly) >= 6:
            last_q = monthly.iloc[-3:].sum()
            prev_q = monthly.iloc[-6:-3].sum()
            if prev_q:
                delta_tri = float((last_q - prev_q) / prev_q)

    return pd.DataFrame(
        [
            {
                "total": total,
                "procedentes": procedentes,
                "improcedentes": improcedentes,
                "pct_procedentes": round(pct_proc, 4),
                "reincidentes_clientes": reincidentes,
                "valor_medio_fatura": round(valor_medio, 2),
                "categorias_count": categorias_count,
                "top3_share": round(top3_share, 4),
                "delta_trimestre": round(delta_tri, 4),
            }
        ]
    )


def sp_severidade_mensal(frame: pd.DataFrame, *, severidade: str = "high") -> pd.DataFrame:
    """Série mensal de volume para SP filtrado por severidade."""
    cols = ["mes_ingresso", "qtd_erros", "procedentes", "improcedentes"]
    df = _filter_sp_severidade(frame, severidade)
    if df.empty or "mes_ingresso" not in df.columns:
        return pd.DataFrame(columns=cols)
    proc_col = "procedente_real" if "procedente_real" in df.columns else "flag_resolvido_com_refaturamento"
    monthly = (
        df.dropna(subset=["mes_ingresso"])
        .assign(
            procedente=lambda x: x[proc_col].fillna(False).astype(bool),
        )
        .groupby("mes_ingresso", as_index=False)
        .agg(
            qtd_erros=("ordem", "nunique"),
            procedentes=("procedente", "sum"),
        )
        .sort_values("mes_ingresso")
    )
    monthly["improcedentes"] = monthly["qtd_erros"] - monthly["procedentes"]
    monthly["procedentes"] = monthly["procedentes"].astype(int)
    monthly["improcedentes"] = monthly["improcedentes"].astype(int)
    monthly["mes_ingresso"] = monthly["mes_ingresso"].astype(str)
    return monthly


def sp_severidade_categorias(
    frame: pd.DataFrame, *, severidade: str = "high", limit: int = 12
) -> pd.DataFrame:
    """Distribuição por categoria taxonômica para SP filtrado por severidade."""
    cols = ["categoria_id", "categoria", "vol", "pct"]
    df = _filter_sp_severidade(frame, severidade)
    if df.empty:
        return pd.DataFrame(columns=cols)
    grouped = (
        df.groupby("categoria", as_index=False)
        .agg(vol=("ordem", "nunique"))
        .sort_values("vol", ascending=False)
    )
    total = float(grouped["vol"].sum()) or 1.0
    grouped["pct"] = (grouped["vol"] / total * 100).round(2)
    grouped["categoria_id"] = grouped["categoria"].str.replace(r"[^a-z0-9]+", "_", regex=True)
    head = grouped.head(limit).copy()
    if len(grouped) > limit:
        rest_vol = int(grouped.iloc[limit:]["vol"].sum())
        rest_pct = round(rest_vol / total * 100, 2)
        head = pd.concat(
            [
                head,
                pd.DataFrame(
                    [
                        {
                            "categoria_id": "outros",
                            "categoria": f"Demais ({len(grouped) - limit})",
                            "vol": rest_vol,
                            "pct": rest_pct,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    return head[cols]


def sp_severidade_causas(
    frame: pd.DataFrame, *, severidade: str = "high", limit: int = 14
) -> pd.DataFrame:
    """Dispersão causa canônica × volume × procedência × reincidência (SP)."""
    cols = ["id", "nome", "vol", "proc", "reinc", "cat"]
    df = _filter_sp_severidade(frame, severidade)
    if df.empty:
        return pd.DataFrame(columns=cols)

    proc_col = "procedente_real" if "procedente_real" in df.columns else "flag_resolvido_com_refaturamento"
    vol = df.groupby("causa_canonica")["ordem"].nunique()
    proc = (
        df.groupby("causa_canonica")[proc_col]
        .apply(lambda s: float(s.fillna(False).astype(bool).mean()) * 100)
    )
    cat = df.groupby("causa_canonica")["categoria"].agg(lambda s: s.mode().iat[0] if len(s) else "")
    reinc = (
        df.loc[df["instalacao_hash"].ne("")]
        .groupby(["causa_canonica", "instalacao_hash"])["ordem"]
        .nunique()
        .reset_index()
        .groupby("causa_canonica")["ordem"]
        .apply(lambda s: int((s > 1).sum()))
    )

    out = (
        pd.DataFrame({"vol": vol, "proc": proc.round(2), "reinc": reinc, "cat": cat})
        .reset_index()
        .rename(columns={"causa_canonica": "nome"})
    )
    out["reinc"] = out["reinc"].fillna(0).astype(int)
    out = out.sort_values("vol", ascending=False).head(limit)
    out.insert(0, "id", [f"c{i+1:02d}" for i in range(len(out))])
    return out[cols]


def sp_severidade_ranking(
    frame: pd.DataFrame, *, severidade: str = "high", limit: int = 10
) -> pd.DataFrame:
    """Top-N instalações reincidentes em SP para a severidade escolhida."""
    cols = ["inst", "cat", "causa", "reinc", "valor", "spark", "cidade"]
    df = _filter_sp_severidade(frame, severidade)
    if df.empty:
        return pd.DataFrame(columns=cols)

    df = df.loc[df["instalacao_hash"].ne("")].copy()
    if df.empty:
        return pd.DataFrame(columns=cols)

    grouped = df.groupby("instalacao_hash")
    reinc = grouped["ordem"].nunique()
    top_idx = reinc.loc[reinc > 1].sort_values(ascending=False).head(limit).index
    if len(top_idx) == 0:
        return pd.DataFrame(columns=cols)

    inst_labels = grouped["instalacao"].agg(
        lambda s: s.dropna().astype(str).iloc[0] if s.dropna().size else ""
    )
    top_cat = grouped["categoria"].agg(lambda s: s.mode().iat[0] if len(s) else "")
    top_causa = grouped["causa_canonica"].agg(lambda s: s.mode().iat[0] if len(s) else "")

    valor_col = (
        "valor_fatura_reclamada_medio"
        if "valor_fatura_reclamada_medio" in df.columns
        else None
    )
    valor = grouped[valor_col].mean() if valor_col else pd.Series(0.0, index=reinc.index)

    cidade_col = "municipio" if "municipio" in df.columns else None
    cidade = (
        grouped[cidade_col].agg(lambda s: s.mode().iat[0] if len(s) else "SP")
        if cidade_col
        else pd.Series("SP", index=reinc.index)
    )

    records: list[dict] = []
    for hash_key in top_idx:
        sub = df.loc[df["instalacao_hash"].eq(hash_key)]
        spark = (
            sub.dropna(subset=["mes_ingresso"])
            .groupby("mes_ingresso")["ordem"]
            .nunique()
            .sort_index()
            .tail(9)
            .astype(int)
            .tolist()
        )
        if len(spark) < 9:
            spark = [0] * (9 - len(spark)) + spark
        records.append(
            {
                "inst": inst_labels.loc[hash_key] or f"INS-{hash_key[:7].upper()}",
                "cat": top_cat.loc[hash_key],
                "causa": top_causa.loc[hash_key],
                "reinc": int(reinc.loc[hash_key]),
                "valor": float(valor.loc[hash_key]) if pd.notna(valor.loc[hash_key]) else 0.0,
                "spark": spark,
                "cidade": f"{cidade.loc[hash_key]}/SP" if cidade.loc[hash_key] else "SP",
            }
        )
    return pd.DataFrame(records, columns=cols)


_AREA_BY_CATEGORIA = {
    "leitura": "Field — Leituristas",
    "medidor": "Field — Manutenção / Medição",
    "consumo": "Comercial — Análise de Consumo",
    "faturamento": "Faturamento / Refaturamento",
    "cadastro": "CRM — Cadastro & Titularidade",
    "atendimento": "Atendimento — Canais",
    "tecnico": "Operacional — Técnica",
}


def _suggest_action(causa: str, categoria: str, proc: bool) -> str:
    base = {
        "leitura_anomala": "Reagendar leitura presencial e validar histórico de 6m da instalação.",
        "leitura_estimada": "Forçar leitura presencial; bloquear estimativa por 2 ciclos.",
        "medidor_danificado": "Abrir OS de troca de medidor; congelar fatura até inspeção.",
        "medidor_avariado": "Inspeção técnica + troca preventiva; revisar consumo dos 3 ciclos anteriores.",
        "consumo_elevado_revisao": "Disparar análise de carga + comparativo sazonal e comunicar cliente em 48h.",
        "refaturamento_corretivo": "Refaturar conforme cálculo regulatório; notificar cliente via canal preferencial.",
        "procedimento_administrativo": "Encerrar ordem com nota administrativa; sem necessidade de ação técnica.",
        "ajuste_numerico_sem_causa": "Validar planilha de ajuste com Faturamento; documentar no run_id atual.",
        "texto_incompleto": "Solicitar reabertura com descrição completa antes de classificar.",
        "solicitacao_canal_atendimento": "Encaminhar para canal correto; sem necessidade de OS técnica.",
    }
    fallback = (
        "Investigar causa-raiz específica desta categoria antes de qualquer ação corretiva."
        if proc
        else "Confirmar improcedência via revisão amostral e arquivar com justificativa."
    )
    return base.get(causa, fallback)


def _resumo_text(text: str, max_len: int = 220) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rsplit(" ", 1)[0] + "…"


def sp_severidade_descricoes(
    frame: pd.DataFrame, *, severidade: str = "high", limit: int = 12
) -> pd.DataFrame:
    """Top descrições normalizadas pelo classificador para a severidade SP escolhida.

    Cada linha representa uma ordem real (texto cleaned do silver) e expõe a
    causa canônica + categoria atribuídas. Inclui ``top_instalacoes`` (até 10)
    para drill-down: instalações com maior reincidência na mesma causa.
    """
    cols = [
        "id",
        "cat",
        "categoria_id",
        "causa",
        "data",
        "proc",
        "valor",
        "resumo",
        "sugestao",
        "area",
        "top_instalacoes",
    ]
    df = _filter_sp_severidade(frame, severidade)
    if df.empty:
        return pd.DataFrame(columns=cols)

    text_candidates = [
        c for c in ("texto_completo", "observacao_ordem", "assunto") if c in df.columns
    ]
    text_col = text_candidates[0] if text_candidates else None

    work = df.copy()
    if text_col is not None:
        work = work.dropna(subset=[text_col])
    if work.empty:
        return pd.DataFrame(columns=cols)

    def _row_text(row: pd.Series) -> str:
        parts: list[str] = []
        if text_col and pd.notna(row.get(text_col)):
            parts.append(str(row[text_col]))
        topic_name = row.get("topic_name")
        if isinstance(topic_name, str) and topic_name and topic_name not in parts[0:1]:
            parts.append(topic_name)
        kws = row.get("topic_keywords")
        if isinstance(kws, str) and kws:
            parts.append(kws.replace(",", ", "))
        elif isinstance(kws, (list, tuple)):
            parts.append(", ".join(str(k) for k in kws if k))
        return " — ".join(p for p in parts if p).strip()

    work["__text"] = work.apply(_row_text, axis=1)
    work = work.loc[work["__text"].astype(str).str.len() > 0]
    if work.empty:
        return pd.DataFrame(columns=cols)
    work["__len"] = work["__text"].str.len()

    work["proc"] = work.get(
        "flag_resolvido_com_refaturamento", pd.Series(False, index=work.index)
    ).fillna(False).astype(bool)
    work["data_ingresso"] = pd.to_datetime(work.get("data_ingresso"), errors="coerce")

    valor_col = (
        "valor_fatura_reclamada_medio"
        if "valor_fatura_reclamada_medio" in work.columns
        else None
    )
    work["__valor"] = work[valor_col] if valor_col else 0.0

    causa_to_top_inst: dict[str, list[dict]] = {}
    if "instalacao_hash" in df.columns:
        eligible = df.loc[df["instalacao_hash"].astype(str).ne("")].copy()
        if not eligible.empty:
            for causa, sub in eligible.groupby("causa_canonica", sort=False):
                inst_grp = sub.groupby("instalacao_hash")
                reinc = inst_grp["ordem"].nunique().sort_values(ascending=False)
                top = reinc.head(10)
                inst_label = inst_grp["instalacao"].agg(
                    lambda s: s.dropna().astype(str).iloc[0] if s.dropna().size else ""
                )
                cidade = (
                    inst_grp["municipio"].agg(
                        lambda s: s.mode().iat[0] if len(s) else ""
                    )
                    if "municipio" in eligible.columns
                    else pd.Series("", index=reinc.index)
                )
                valor_per_inst = (
                    inst_grp[valor_col].mean()
                    if valor_col
                    else pd.Series(0.0, index=reinc.index)
                )
                items: list[dict] = []
                for hash_key, count in top.items():
                    items.append(
                        {
                            "inst": inst_label.get(hash_key, "")
                            or f"INS-{str(hash_key)[:7].upper()}",
                            "cidade": str(cidade.get(hash_key, "")) or "SP",
                            "reinc": int(count),
                            "valor": float(valor_per_inst.get(hash_key, 0.0) or 0.0),
                        }
                    )
                causa_to_top_inst[str(causa)] = items

    work = work.sort_values(["__valor", "__len"], ascending=[False, True]).head(limit * 4)

    seen: set[str] = set()
    records: list[dict] = []
    for _, row in work.iterrows():
        causa = str(row.get("causa_canonica") or "indefinido")
        cat = str(row.get("categoria") or "nao_classificada")
        ordem_id = str(row.get("ordem") or "")
        bucket_key = ordem_id or f"{causa}::{bool(row['proc'])}::{len(records)}"
        if bucket_key in seen:
            continue
        seen.add(bucket_key)
        records.append(
            {
                "id": f"ORD-{ordem_id}" if ordem_id else f"ENL-{len(records):04d}",
                "cat": cat.replace("_", " ").title(),
                "categoria_id": cat,
                "causa": causa,
                "data": row["data_ingresso"].strftime("%Y-%m-%d")
                if pd.notna(row["data_ingresso"])
                else "",
                "proc": bool(row["proc"]),
                "valor": float(row["__valor"]) if pd.notna(row["__valor"]) else 0.0,
                "resumo": _resumo_text(str(row.get("__text", ""))),
                "sugestao": _suggest_action(causa, cat, bool(row["proc"])),
                "area": _AREA_BY_CATEGORIA.get(cat, "Operacional — Triagem"),
                "top_instalacoes": causa_to_top_inst.get(causa, [])[:10],
            }
        )
        if len(records) >= limit:
            break

    return pd.DataFrame(records, columns=cols)


def sp_categoria_subcausa_tree(
    frame: pd.DataFrame,
    *,
    severidade: str | tuple[str, ...] | list[str] = ("high", "critical", "medium", "low"),
    top_categorias: int = 8,
    top_subcausas: int = 6,
) -> pd.DataFrame:
    """Árvore categoria → causa canônica (subcausa) → exemplo real do silver.

    Saída longa: cada linha é uma subcausa dentro de uma categoria, com
    contagens exatas (procedentes/improcedentes), percentual sobre a categoria
    e um exemplo real (texto cleaned). Não inventa exemplo: se não houver,
    o campo `exemplo_descricao` fica vazio.
    """
    cols = [
        "categoria_id",
        "categoria_label",
        "categoria_qtd",
        "categoria_pct",
        "subcausa_id",
        "subcausa_label",
        "qtd",
        "percentual_na_categoria",
        "procedentes",
        "improcedentes",
        "exemplo_id",
        "exemplo_data",
        "exemplo_descricao",
        "exemplo_status",
        "exemplo_valor_fatura",
        "recomendacao_operacional",
    ]
    df = _filter_sp_severidade(frame, severidade)
    if df.empty:
        return pd.DataFrame(columns=cols)

    work = df.copy()
    work["categoria"] = work.get("categoria", pd.Series("nao_classificada", index=work.index)).fillna("nao_classificada").astype(str)
    work["causa_canonica"] = work.get("causa_canonica", pd.Series("indefinido", index=work.index)).fillna("indefinido").astype(str)
    proc_col = "procedente_real" if "procedente_real" in work.columns else "flag_resolvido_com_refaturamento"
    work["proc"] = work.get(proc_col, pd.Series(False, index=work.index)).fillna(False).astype(bool)

    text_candidates = [c for c in ("texto_completo", "observacao_ordem", "assunto") if c in work.columns]
    text_col = text_candidates[0] if text_candidates else None
    valor_col = "valor_fatura_reclamada_medio" if "valor_fatura_reclamada_medio" in work.columns else None
    work["__valor"] = work[valor_col] if valor_col else 0.0
    work["data_ingresso"] = pd.to_datetime(work.get("data_ingresso"), errors="coerce")

    cat_totals = work.groupby("categoria")["ordem"].nunique().sort_values(ascending=False)
    overall_total = max(int(cat_totals.sum()), 1)
    top_cat_index = cat_totals.head(top_categorias).index.tolist()
    work = work.loc[work["categoria"].isin(top_cat_index)]
    if work.empty:
        return pd.DataFrame(columns=cols)

    rows: list[dict] = []
    for categoria, cat_df in work.groupby("categoria", sort=False):
        cat_qtd = int(cat_df["ordem"].nunique())
        cat_pct = round(cat_qtd / overall_total * 100, 2)
        causa_groups = (
            cat_df.groupby("causa_canonica", as_index=False)
            .agg(
                qtd=("ordem", "nunique"),
                proc_sum=("proc", "sum"),
            )
            .sort_values("qtd", ascending=False)
            .head(top_subcausas)
        )
        for _, sub in causa_groups.iterrows():
            causa = str(sub["causa_canonica"])
            qtd = int(sub["qtd"])
            proc = int(sub["proc_sum"])
            improc = qtd - proc
            pct_cat = round(qtd / max(cat_qtd, 1) * 100, 2)

            sub_df = cat_df.loc[cat_df["causa_canonica"].eq(causa)].copy()
            example: dict[str, object] = {
                "exemplo_id": "",
                "exemplo_data": "",
                "exemplo_descricao": "",
                "exemplo_status": "",
                "exemplo_valor_fatura": 0.0,
            }
            if text_col is not None:
                texts = sub_df[text_col].fillna("").astype(str).str.strip()
                sub_df = sub_df.assign(__text=texts)
                sub_df = sub_df.loc[sub_df["__text"].str.len() > 0]
            if not sub_df.empty:
                sub_df = sub_df.sort_values(["__valor"], ascending=False)
                pick = sub_df.iloc[0]
                example["exemplo_id"] = (
                    f"ORD-{pick.get('ordem')}" if pd.notna(pick.get("ordem")) else ""
                )
                example["exemplo_data"] = (
                    pick["data_ingresso"].strftime("%Y-%m-%d")
                    if pd.notna(pick.get("data_ingresso"))
                    else ""
                )
                example["exemplo_descricao"] = _resumo_text(str(pick.get("__text", "")))
                example["exemplo_status"] = "procedente" if bool(pick["proc"]) else "improcedente"
                example["exemplo_valor_fatura"] = (
                    float(pick["__valor"]) if pd.notna(pick.get("__valor")) else 0.0
                )

            rows.append(
                {
                    "categoria_id": str(categoria),
                    "categoria_label": str(categoria).replace("_", " ").title(),
                    "categoria_qtd": cat_qtd,
                    "categoria_pct": cat_pct,
                    "subcausa_id": causa,
                    "subcausa_label": causa,
                    "qtd": qtd,
                    "percentual_na_categoria": pct_cat,
                    "procedentes": proc,
                    "improcedentes": improc,
                    "recomendacao_operacional": _suggest_action(causa, str(categoria), proc > improc),
                    **example,
                }
            )
    return pd.DataFrame(rows, columns=cols)


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
    return _canonical_cause_frame(frame)["causa_canonica"]


def _canonical_cause_frame(frame: pd.DataFrame) -> pd.DataFrame:
    cols = ["causa_canonica", "causa_canonica_confidence"]
    if frame.empty:
        return pd.DataFrame(columns=cols, index=frame.index)

    if "causa_canonica_v3" in frame.columns:
        labels = frame["causa_canonica_v3"].map(canonical_label).fillna(
            frame["causa_canonica_v3"].fillna("").astype(str)
        )
        labels = labels.replace({"": "indefinido", "nan": "indefinido"}).fillna("indefinido")
        confidence = (
            frame.get("causa_canonica_confidence", pd.Series("high", index=frame.index))
            .fillna("high")
            .astype(str)
            .where(lambda s: s.isin(["high", "low", "indefinido"]), "high")
        )
        return pd.DataFrame(
            {"causa_canonica": labels.astype(str), "causa_canonica_confidence": confidence},
            index=frame.index,
        )

    labels = frame.get("causa_raiz", pd.Series(index=frame.index, dtype=object))
    canonical = labels.map(canonical_label)
    confidence = pd.Series("high", index=frame.index, dtype=object)
    missing = canonical.isna()
    confidence.loc[missing] = "indefinido"
    eligible_for_fallback = frame.get(
        "_data_type",
        pd.Series("", index=frame.index),
    ).isin(TRAINING_DATA_TYPES)
    fallback_mask = missing & eligible_for_fallback
    if fallback_mask.any():
        texts = frame.get("texto_completo", pd.Series("", index=frame.index)).fillna("").astype(str)
        fallback = _keyword_fallback_results(texts.loc[fallback_mask])
        canonical.loc[fallback_mask] = fallback["causa_canonica"]
        confidence.loc[fallback_mask] = fallback["causa_canonica_confidence"]
    total_mask = missing & ~eligible_for_fallback
    if total_mask.any():
        canonical.loc[total_mask] = "reclamacao_total_sem_causa"
        confidence.loc[total_mask] = "indefinido"
    return pd.DataFrame(
        {
            "causa_canonica": canonical.fillna("indefinido").astype(str),
            "causa_canonica_confidence": confidence.fillna("indefinido").astype(str),
        },
        index=frame.index,
    )


def _apply_topic_to_canonical(
    frame: pd.DataFrame,
    topic_to_canonical: pd.DataFrame | None,
) -> pd.DataFrame:
    if (
        frame.empty
        or topic_to_canonical is None
        or topic_to_canonical.empty
        or "topic_id" not in frame.columns
    ):
        return frame
    required = {"topic_id", "canonical_target", "confidence"}
    if not required.issubset(topic_to_canonical.columns):
        return frame
    mapping = topic_to_canonical[list(required)].copy()
    mapping["topic_id"] = mapping["topic_id"].astype(str)
    mapping = mapping.rename(
        columns={
            "canonical_target": "_topic_canonical_target",
            "confidence": "_topic_confidence",
        }
    )
    out = frame.merge(mapping, on="topic_id", how="left")
    apply_mask = (
        out["causa_canonica"].astype(str).eq("indefinido")
        & out["_topic_canonical_target"].notna()
    )
    out.loc[apply_mask, "causa_canonica"] = out.loc[apply_mask, "_topic_canonical_target"]
    out.loc[apply_mask, "causa_canonica_confidence"] = out.loc[
        apply_mask, "_topic_confidence"
    ].fillna("low")
    return out.drop(columns=["_topic_canonical_target", "_topic_confidence"])


def _keyword_label_or_indefinido(classifier: KeywordErroLeituraClassifier, text: str) -> str:
    """Usa classificador v2 (com threshold e ambiguidade). Retorna `indefinido`
    apenas quando o texto realmente nao tem sinal — reduz drasticamente o bucket
    generico em SP que antes caia em `outros`."""
    result = classifier.classify(text)
    return str(result["classe"])


def _keyword_result(classifier: KeywordErroLeituraClassifier, text: str) -> dict[str, str]:
    result = classifier.classify(text)
    return {
        "causa_canonica": str(result["classe"]),
        "causa_canonica_confidence": str(result.get("confidence", "indefinido")),
    }


def _keyword_fallback_labels(
    texts: pd.Series,
    *,
    cache_dir: Path = Path(".streamlit/cache"),
) -> pd.Series:
    results = _keyword_fallback_results(texts, cache_dir=cache_dir)
    return results["causa_canonica"]


def _keyword_fallback_results(
    texts: pd.Series,
    *,
    cache_dir: Path = Path(".streamlit/cache"),
) -> pd.DataFrame:
    if texts.empty:
        return pd.DataFrame(
            columns=["causa_canonica", "causa_canonica_confidence"],
            index=texts.index,
        )

    cache_path = cache_dir / f"erro_leitura_keyword_labels_{KEYWORD_LABEL_CACHE_VERSION}.pkl"
    cache: dict[str, dict[str, str]] = _read_keyword_label_cache(cache_path)
    normalized = texts.fillna("").astype(str).map(normalize_text)
    digests = normalized.map(lambda text: sha256(text.encode()).hexdigest())
    missing_digests = set(digests.unique()).difference(cache)

    if missing_digests:
        classifier = KeywordErroLeituraClassifier()
        new_labels: dict[str, dict[str, str]] = {}
        unique_pairs = pd.DataFrame(
            {"digest": digests, "text": normalized}
        ).drop_duplicates("digest")
        for row in unique_pairs.itertuples(index=False):
            if row.digest in missing_digests:
                new_labels[row.digest] = _keyword_result(classifier, row.text)
        cache.update(new_labels)
        _write_keyword_label_cache(cache_path, cache)

    rows = digests.map(cache).tolist()
    return pd.DataFrame(rows, index=texts.index).fillna(
        {"causa_canonica": "indefinido", "causa_canonica_confidence": "indefinido"}
    )


def _read_keyword_label_cache(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            value = pickle.load(handle)
    except (OSError, pickle.PickleError, EOFError):
        return {}
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for key, payload in value.items():
        if isinstance(payload, dict):
            label = str(payload.get("causa_canonica", "indefinido"))
            confidence = str(payload.get("causa_canonica_confidence", "indefinido"))
        else:
            label = str(payload)
            confidence = "indefinido" if label == "indefinido" else "high"
        normalized[str(key)] = {
            "causa_canonica": label,
            "causa_canonica_confidence": confidence,
        }
    return normalized


def _write_keyword_label_cache(path: Path, cache: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        pickle.dump(cache, handle)
    tmp.replace(path)


def _to_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.casefold().isin({"true", "1", "sim", "yes"})


def _attach_procedencia_real_legacy_status(frame: pd.DataFrame) -> pd.DataFrame:
    """Legacy fallback: derive procedência from `status` text + refat flag.

    Kept for environments where the clusterized CSV is missing. Not used by
    the active pipeline, which now joins NOTA RL → ordem against
    `_load_procedencia_lookup()` for ground-truth labels.
    """
    if frame.empty:
        out = frame.copy()
        out["procedencia_real"] = pd.Series(dtype=str)
        return out

    out = frame.copy()
    existing = _to_bool(
        out.get("flag_resolvido_com_refaturamento", pd.Series(False, index=out.index))
    )
    status = (
        out.get("status", pd.Series("", index=out.index))
        .fillna("")
        .astype(str)
        .str.casefold()
    )
    explicit_improc = status.str.contains("improced", regex=False)
    explicit_proc = status.str.contains("proced", regex=False) & ~explicit_improc

    procedencia = pd.Series("NAO_INFORMADA", index=out.index, dtype=str)
    procedencia = procedencia.mask(existing, "PROCEDENTE")
    procedencia = procedencia.mask(~existing, "IMPROCEDENTE")
    procedencia = procedencia.mask(explicit_proc, "PROCEDENTE")
    procedencia = procedencia.mask(explicit_improc, "IMPROCEDENTE")

    out["procedencia_real"] = procedencia
    out["flag_resolvido_com_refaturamento"] = explicit_proc.where(
        explicit_proc | explicit_improc,
        existing,
    )
    return out


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


def _taxonomy_example(value: object) -> str:
    text = _mask_sensitive_text(value)
    if len(text) <= MAX_TAXONOMY_EXAMPLE_CHARS:
        return text
    return f"{text[:MAX_TAXONOMY_EXAMPLE_CHARS].rstrip()}..."


def _mask_sensitive_text(value: object) -> str:
    text = "" if value is None or pd.isna(value) else str(value)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}\b", "[EMAIL]", text)
    text = re.sub(r"\bbr\d{5,}\b", "br[ID_INTERNO]", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bgmtuk\s+[^()*\n\r]{3,80}\s+\(br\[?ID_INTERNO\]?\)",
        "gmtuk [USUARIO] (br[ID_INTERNO])",
        text,
    )
    text = re.sub(
        r"\bgmtuk\s+[a-zA-ZÀ-ÿ\s]{3,100}?"
        r"(?=\s+(?:cliente|clt|reclama|solicita|trata|erro|segue|\*|$))",
        "gmtuk [USUARIO]",
        text,
    )
    text = re.sub(
        r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}",
        "[TELEFONE]",
        text,
    )
    text = re.sub(r"\b\d{5}-?\d{3}\b", "[CEP]", text)
    text = re.sub(r"\b(?:protocolo|prot)\s*[:#-]?\s*\d{6,}\b", "protocolo [PROTOCOLO]", text)
    text = re.sub(r"\b((?:celular|telefone|tel))\s*:\s*\d+\b", r"\1: [TELEFONE]", text)
    return text


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
