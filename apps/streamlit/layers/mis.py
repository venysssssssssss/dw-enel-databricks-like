from __future__ import annotations

from typing import Any

import plotly.express as px

from apps.streamlit.components.narrative import LayerNarrative, download_dataframe, layer_intro
from apps.streamlit.layers.common import aggregate, render_chart, render_table_or_empty
from apps.streamlit.theme import SEQUENTIAL_BLUE, SEQUENTIAL_ORANGE
from src.viz.erro_leitura_dashboard_data import (
    mis_executive_summary,
    mis_monthly_mis,
    severity_heatmap,
    taxonomy_reference,
)


def render(st: Any, frame, *, theme: str = "light") -> None:
    layer_intro(
        st,
        LayerNarrative(
            icon="🧭",
            title="BI MIS Executivo",
            question="Qual é a fotografia executiva de volume, severidade e reincidência?",
            method="Resumo por região, tendência mensal MIS e severidade da taxonomia.",
            action="Use esta aba para alinhar diretoria e depois aprofunde por causa ou tópico.",
        ),
    )
    summary = aggregate(mis_executive_summary, frame)
    monthly = aggregate(mis_monthly_mis, frame)
    severity = aggregate(severity_heatmap, frame)

    render_table_or_empty(st, summary, section="mis_executivo")
    if not monthly.empty:
        fig = px.line(
            monthly,
            x="mes_ingresso",
            y="qtd_erros",
            color="regiao",
            markers=True,
            line_shape="spline",
            title="Tendência mensal por região",
        )
        render_chart(st, fig, key="mis_monthly", theme=theme)
        download_dataframe(st, "📥 CSV tendência MIS", monthly, section="mis_tendencia")
    if not severity.empty:
        fig = px.density_heatmap(
            severity,
            x="severidade",
            y="regiao",
            z="qtd_erros",
            color_continuous_scale=SEQUENTIAL_ORANGE + SEQUENTIAL_BLUE,
            title="Severidade por região",
        )
        render_chart(st, fig, key="mis_severity", theme=theme, height=360)
    with st.expander("Referência de taxonomia operacional"):
        render_table_or_empty(st, taxonomy_reference(), section="taxonomia_referencia")
