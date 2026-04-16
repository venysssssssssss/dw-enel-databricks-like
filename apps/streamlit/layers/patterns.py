from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px

from apps.streamlit.components.narrative import LayerNarrative, download_dataframe, layer_intro
from apps.streamlit.layers.common import (
    aggregate,
    color_sequence,
    render_chart,
    render_table_or_empty,
)
from apps.streamlit.theme import SEQUENTIAL_BLUE, SEQUENTIAL_GREEN
from src.viz.erro_leitura_dashboard_data import (
    radar_causes_by_region,
    region_cause_matrix,
    topic_distribution,
)


def render(st: Any, frame, *, theme: str = "light") -> None:
    layer_intro(
        st,
        LayerNarrative(
            icon="🗺",
            title="Padrões & Concentrações",
            question="Quais padrões se repetem por região, causa e tópico de IA?",
            method="Heatmap região × causa, ranking de tópicos e radar comparativo CE/SP.",
            action="Use tópico e causa como hipóteses para atacar clusters operacionais.",
        ),
    )
    matrix = aggregate(region_cause_matrix, frame)
    topics = aggregate(topic_distribution, frame, limit=14)
    radar = aggregate(radar_causes_by_region, frame, top_n=10)

    if not matrix.empty:
        long_matrix = matrix.melt(
            id_vars="causa_canonica",
            var_name="regiao",
            value_name="qtd_erros",
        )
        fig = px.density_heatmap(
            long_matrix,
            x="regiao",
            y="causa_canonica",
            z="qtd_erros",
            color_continuous_scale=SEQUENTIAL_BLUE,
            title="Concentração região × causa",
            labels={"regiao": "Região", "causa_canonica": "Causa", "qtd_erros": "Ordens"},
            text_auto=True,
        )
        fig.update_traces(
            hovertemplate="<b>%{y}</b> · %{x}<br>%{z:,d} ordens<extra></extra>",
            textfont={"size": 10, "color": "#0C1420"},
        )
        fig.update_layout(coloraxis_colorbar={"title": "Ordens", "thickness": 12})
        render_chart(st, fig, key="patterns_heatmap", theme=theme, height=520, on_select="rerun")
        download_dataframe(st, "📥 CSV heatmap", long_matrix, section="padroes_heatmap")

    left, right = st.columns([1.1, 1])
    with left:
        if topics.empty:
            render_table_or_empty(st, topics, section="padroes_topicos")
        else:
            fig = px.bar(
                topics,
                x="qtd_erros",
                y="topic_name",
                orientation="h",
                color="taxa_refaturamento",
                color_continuous_scale=SEQUENTIAL_GREEN,
                hover_data={"topic_keywords": True, "taxa_refaturamento": ":.1%"},
                title="Tópicos IA mais recorrentes",
                labels={
                    "qtd_erros": "Ordens",
                    "topic_name": "Tópico",
                    "taxa_refaturamento": "Refaturamento",
                    "topic_keywords": "Palavras-chave",
                },
            )
            fig.update_yaxes(categoryorder="total ascending")
            fig.update_layout(coloraxis_colorbar={"title": "Refat.", "tickformat": ".0%"})
            render_chart(st, fig, key="patterns_topics", theme=theme, on_select="rerun")
            download_dataframe(st, "📥 CSV tópicos", topics, section="padroes_topicos")
    with right:
        if not radar.empty:
            radar_plot = radar.copy()
            radar_plot["percentual"] = pd.to_numeric(radar_plot["percentual"]) * 100
            fig = px.line_polar(
                radar_plot,
                r="percentual",
                theta="causa_canonica",
                color="regiao",
                line_close=True,
                title="Perfil relativo por região",
                color_discrete_sequence=color_sequence(),
            )
            fig.update_traces(
                fill="toself",
                opacity=0.45,
                hovertemplate="<b>%{theta}</b><br>%{fullData.name}: %{r:.1f}%<extra></extra>",
            )
            fig.update_layout(
                polar={
                    "radialaxis": {
                        "ticksuffix": "%",
                        "tickfont": {"size": 10},
                        "gridcolor": "rgba(15, 76, 129, 0.10)",
                    },
                    "angularaxis": {"tickfont": {"size": 11}},
                    "bgcolor": "rgba(0,0,0,0)",
                },
            )
            render_chart(st, fig, key="patterns_radar", theme=theme, height=460)
