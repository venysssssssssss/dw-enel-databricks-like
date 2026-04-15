from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.express as px

from apps.streamlit.components.narrative import LayerNarrative, download_dataframe, layer_intro
from apps.streamlit.layers.common import render_chart, render_table_or_empty
from apps.streamlit.theme import SEQUENTIAL_BLUE, format_int, format_pct
from src.viz.cache import load_or_build_disk_cache, path_fingerprint
from src.viz.reclamacoes_ce_dashboard_data import (
    RECLAMACOES_CE_CACHE_VERSION,
    assunto_pareto,
    compute_kpis,
    cruzamento_com_erro_leitura,
    executive_summary,
    heatmap_tema_x_mes,
    load_reclamacoes_ce,
    macro_tema_distribution,
    monthly_trend_by_tema,
    top_instalacoes_reincidentes,
)


def render(st: Any, *, silver_path: Path, erro_leitura_frame, theme: str = "light") -> None:
    layer_intro(
        st,
        LayerNarrative(
            icon="🟧",
            title="CE · Reclamações Totais",
            question="Quais temas dominam as reclamações CE e onde erro de leitura cruza com elas?",
            method=(
                "Classificação macro por assunto, recorrência por instalação e cruzamento "
                "por hash."
            ),
            action="Investigue temas com alto cruzamento para provar causa-raiz indireta.",
        ),
    )
    frame = _load_reclamacoes(st, silver_path)
    if frame.empty:
        render_table_or_empty(st, frame, section="reclamacoes_ce")
        return

    kpis = compute_kpis(frame)
    cols = st.columns(5)
    cols[0].metric("Reclamações CE", format_int(kpis.total_reclamacoes))
    cols[1].metric("Instalações únicas", format_int(kpis.unique_instalacoes))
    cols[2].metric("Reincidentes", format_int(kpis.instalacoes_reincidentes))
    cols[3].metric("% Grupo B", format_pct(kpis.share_grupo_b))
    cols[4].metric("Tema dominante", kpis.tema_dominante, format_pct(kpis.share_tema_dominante))

    precomputed = _precompute_reclamacoes_ce(silver_path, frame)
    dist = precomputed["macro_tema_distribution"]
    trend = monthly_trend_by_tema(frame)
    cross = cruzamento_com_erro_leitura(frame, erro_leitura_frame)
    pareto = assunto_pareto(frame, top_n=20)
    heat = precomputed["heatmap_tema_x_mes"]

    left, right = st.columns([1.05, 1])
    with left:
        fig = px.bar(
            dist,
            x="qtd",
            y="macro_tema_label",
            orientation="h",
            color="percentual",
            color_continuous_scale=SEQUENTIAL_BLUE,
            title="Macrotemas de reclamações CE",
        )
        fig.update_yaxes(categoryorder="total ascending")
        render_chart(st, fig, key="ce_macro", theme=theme, on_select="rerun")
        download_dataframe(st, "📥 CSV macrotemas", dist, section="ce_macrotemas")
    with right:
        fig = px.line(
            trend,
            x="ano_mes",
            y="qtd",
            color="macro_tema_label",
            line_shape="spline",
            title="Tendência mensal por macrotema",
        )
        render_chart(st, fig, key="ce_trend", theme=theme)

    if not cross.empty:
        fig = px.bar(
            cross,
            x="percentual",
            y="macro_tema_label",
            orientation="h",
            color="qtd_com_erro_leitura",
            color_continuous_scale=SEQUENTIAL_BLUE,
            title="Cruzamento com instalações que têm erro de leitura",
        )
        fig.update_yaxes(categoryorder="total ascending")
        render_chart(st, fig, key="ce_cross", theme=theme)
        download_dataframe(st, "📥 CSV cruzamento", cross, section="ce_cruzamento_erro_leitura")

    with st.expander("Pareto de assuntos, heatmap mensal e instalações reincidentes"):
        render_table_or_empty(st, precomputed["executive_summary"], section="ce_resumo_executivo")
        render_table_or_empty(st, pareto, section="ce_pareto_assuntos")
        render_table_or_empty(st, heat.reset_index(), section="ce_heatmap_tema_mes")
        render_table_or_empty(
            st,
            top_instalacoes_reincidentes(frame, top_n=20),
            section="ce_instalacoes_reincidentes",
        )


def _load_reclamacoes(st: Any, silver_path: Path):
    @st.cache_data(show_spinner="Carregando reclamações CE...")
    def _cached(path: str, mtime_ns: int):
        del mtime_ns
        return load_reclamacoes_ce(Path(path))

    mtime_ns = silver_path.stat().st_mtime_ns if silver_path.exists() else 0
    return _cached(str(silver_path), mtime_ns)


def _precompute_reclamacoes_ce(silver_path: Path, frame):
    signature = f"{path_fingerprint(silver_path)}_{RECLAMACOES_CE_CACHE_VERSION}_precompute_v1"

    def _builder():
        return {
            "executive_summary": executive_summary(frame),
            "macro_tema_distribution": macro_tema_distribution(frame),
            "heatmap_tema_x_mes": heatmap_tema_x_mes(frame),
        }

    return load_or_build_disk_cache(
        Path(".streamlit/cache"),
        "reclamacoes_ce_precompute",
        signature,
        _builder,
    )
