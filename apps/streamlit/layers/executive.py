from __future__ import annotations

from typing import Any

import plotly.express as px

from apps.streamlit.components.narrative import LayerNarrative, download_dataframe, layer_intro
from apps.streamlit.layers.common import (
    aggregate,
    color_sequence,
    render_chart,
    render_table_or_empty,
)
from apps.streamlit.theme import SEQUENTIAL_BLUE
from src.viz.erro_leitura_dashboard_data import monthly_volume, root_cause_distribution


def render(st: Any, frame, *, theme: str = "light") -> None:
    layer_intro(
        st,
        LayerNarrative(
            icon="📈",
            title="Ritmo Operacional",
            question="O volume está subindo, concentrado em qual região e em qual causa?",
            method="Série mensal por região combinada com Pareto de causa canônica.",
            action="Clique nas barras do Pareto para investigar a causa nas abas seguintes.",
        ),
    )
    monthly = aggregate(monthly_volume, frame)
    causes = aggregate(root_cause_distribution, frame, limit=14)
    left, right = st.columns([1.15, 1])
    with left:
        if not monthly.empty:
            fig = px.area(
                monthly,
                x="mes_ingresso",
                y="qtd_erros",
                color="regiao",
                markers=True,
                title="Volume mensal de erros de leitura",
                color_discrete_sequence=color_sequence(),
                labels={
                    "mes_ingresso": "Mês",
                    "qtd_erros": "Ordens",
                    "regiao": "Região",
                },
            )
            fig.update_traces(
                line={"width": 2.2, "shape": "spline"},
                hovertemplate="<b>%{x|%b/%Y}</b><br>%{fullData.name}: %{y:,d}<extra></extra>",
            )
            render_chart(st, fig, key="executive_monthly", theme=theme)
            download_dataframe(st, "📥 CSV volume mensal", monthly, section="ritmo_volume_mensal")
    with right:
        if causes.empty:
            render_table_or_empty(st, causes, section="ritmo_causas")
        else:
            fig = px.bar(
                causes,
                x="qtd_erros",
                y="causa_canonica",
                orientation="h",
                color="qtd_erros",
                color_continuous_scale=SEQUENTIAL_BLUE,
                title="Pareto de causas canônicas",
                labels={"qtd_erros": "Ordens", "causa_canonica": "Causa"},
                text="qtd_erros",
            )
            fig.update_yaxes(categoryorder="total ascending")
            fig.update_traces(
                texttemplate="%{x:,d}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>%{x:,d} ordens<extra></extra>",
            )
            fig.update_layout(coloraxis_showscale=False)
            render_chart(st, fig, key="executive_causes", theme=theme, on_select="rerun")
            download_dataframe(st, "📥 CSV Pareto", causes, section="ritmo_pareto_causas")
