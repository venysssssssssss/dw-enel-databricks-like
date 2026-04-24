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
DEFAULT_MEDIDOR_SP_PATH = Path("DESCRICOES_ENEL/medidor_20260417_20260416T090000.csv")
DEFAULT_FATURA_SP_PATH = Path("DESCRICOES_ENEL/DADOS_FATURA_SP_ORDENS001.XLSX")
TRAINING_DATA_TYPES = {"erro_leitura", "base_n1_sp"}
KEYWORD_LABEL_CACHE_VERSION = "keyword-v1"
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
    return prepare_dashboard_frame(
        silver,
        topic_assignments=assignments,
        topic_taxonomy=taxonomy,
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
        include_total=True,
    )
    return pd.concat([training_frame, total_frame], ignore_index=True)


def prepare_dashboard_frame(
    silver: pd.DataFrame,
    *,
    topic_assignments: pd.DataFrame | None = None,
    topic_taxonomy: pd.DataFrame | None = None,
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
    frame["causa_canonica"] = _canonical_causes(frame)
    frame["flag_resolvido_com_refaturamento"] = _to_bool(
        frame.get("flag_resolvido_com_refaturamento", pd.Series(False, index=frame.index))
    )
    frame["has_causa_raiz_label"] = _to_bool(
        frame.get("has_causa_raiz_label", pd.Series(False, index=frame.index))
    )
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
        "status",
        "assunto",
        "grupo",
        "instalacao",
        "flag_resolvido_com_refaturamento",
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


def _attach_severidade(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    meta = taxonomy_metadata()[["classe", "categoria", "severidade", "peso_severidade"]]
    merged = frame.merge(meta, left_on="causa_canonica", right_on="classe", how="left")
    merged["severidade"] = merged["severidade"].fillna("low")
    merged["categoria"] = merged["categoria"].fillna("nao_classificada")
    merged["peso_severidade"] = merged["peso_severidade"].fillna(1.0)
    return merged


def _filter_sp_severidade(frame: pd.DataFrame, severidade: str) -> pd.DataFrame:
    sev_key = _SEVERIDADE_ALIAS.get((severidade or "").lower(), severidade)
    df = _attach_severidade(frame)
    if df.empty:
        return df
    if "regiao" in df.columns:
        df = df.loc[df["regiao"].astype(str).str.upper().eq("SP")]
    df = df.loc[df["severidade"].eq(sev_key)]
    return df


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
    procedentes = int(df["flag_resolvido_com_refaturamento"].fillna(False).astype(bool).sum())
    improcedentes = total - procedentes
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
    monthly = (
        df.dropna(subset=["mes_ingresso"])
        .assign(
            procedente=lambda x: x["flag_resolvido_com_refaturamento"].fillna(False).astype(bool),
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

    vol = df.groupby("causa_canonica")["ordem"].nunique()
    proc = (
        df.groupby("causa_canonica")["flag_resolvido_com_refaturamento"]
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

    inst_labels = grouped["instalacao"].agg(lambda s: s.dropna().astype(str).iloc[0] if s.dropna().size else "")
    top_cat = grouped["categoria"].agg(lambda s: s.mode().iat[0] if len(s) else "")
    top_causa = grouped["causa_canonica"].agg(lambda s: s.mode().iat[0] if len(s) else "")

    valor_col = "valor_fatura_reclamada_medio" if "valor_fatura_reclamada_medio" in df.columns else None
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
    eligible_for_fallback = frame.get(
        "_data_type",
        pd.Series("", index=frame.index),
    ).isin(TRAINING_DATA_TYPES)
    fallback_mask = missing & eligible_for_fallback
    if fallback_mask.any():
        texts = frame.get("texto_completo", pd.Series("", index=frame.index)).fillna("").astype(str)
        fallback = _keyword_fallback_labels(texts.loc[fallback_mask])
        canonical.loc[fallback_mask] = fallback
    total_mask = missing & ~eligible_for_fallback
    if total_mask.any():
        canonical.loc[total_mask] = "reclamacao_total_sem_causa"
    return canonical.fillna("indefinido").astype(str)


def _keyword_label_or_indefinido(classifier: KeywordErroLeituraClassifier, text: str) -> str:
    """Usa classificador v2 (com threshold e ambiguidade). Retorna `indefinido`
    apenas quando o texto realmente nao tem sinal — reduz drasticamente o bucket
    generico em SP que antes caia em `outros`."""
    result = classifier.classify(text)
    return str(result["classe"])


def _keyword_fallback_labels(
    texts: pd.Series,
    *,
    cache_dir: Path = Path(".streamlit/cache"),
) -> pd.Series:
    if texts.empty:
        return pd.Series(dtype=str, index=texts.index)

    cache_path = cache_dir / f"erro_leitura_keyword_labels_{KEYWORD_LABEL_CACHE_VERSION}.pkl"
    cache: dict[str, str] = _read_keyword_label_cache(cache_path)
    normalized = texts.fillna("").astype(str).map(normalize_text)
    digests = normalized.map(lambda text: sha256(text.encode()).hexdigest())
    missing_digests = set(digests.unique()).difference(cache)

    if missing_digests:
        classifier = KeywordErroLeituraClassifier()
        new_labels: dict[str, str] = {}
        unique_pairs = pd.DataFrame(
            {"digest": digests, "text": normalized}
        ).drop_duplicates("digest")
        for row in unique_pairs.itertuples(index=False):
            if row.digest in missing_digests:
                new_labels[row.digest] = _keyword_label_or_indefinido(classifier, row.text)
        cache.update(new_labels)
        _write_keyword_label_cache(cache_path, cache)

    return digests.map(cache).fillna("indefinido").astype(str)


def _read_keyword_label_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            value = pickle.load(handle)
    except (OSError, pickle.PickleError, EOFError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(label) for key, label in value.items()}


def _write_keyword_label_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        pickle.dump(cache, handle)
    tmp.replace(path)


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
