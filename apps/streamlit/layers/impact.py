from __future__ import annotations

from typing import Any

import plotly.express as px

from apps.streamlit.components.narrative import LayerNarrative, download_dataframe, layer_intro
from apps.streamlit.layers.common import aggregate, render_chart, render_table_or_empty
from apps.streamlit.theme import SEQUENTIAL_ORANGE
from src.viz.erro_leitura_dashboard_data import (
    category_breakdown,
    refaturamento_by_cause,
    reincidence_matrix,
)


def render(st: Any, frame, *, theme: str = "light") -> None:
    layer_intro(
        st,
        LayerNarrative(
            icon="💰",
            title="Impacto de Refaturamento",
            question="Quais causas geram maior probabilidade de retrabalho financeiro?",
            method="Taxa média de refaturamento por causa, categoria e reincidência.",
            action="Priorize causas com alto volume e alta taxa de refaturamento.",
        ),
    )
    refat = aggregate(refaturamento_by_cause, frame, limit=12)
    categories = aggregate(category_breakdown, frame)
    reincidence = aggregate(reincidence_matrix, frame)

    if not refat.empty:
        refat_plot = refat.copy()
        refat_plot["taxa_refaturamento_pct"] = refat_plot["taxa_refaturamento"] * 100
        fig = px.scatter(
            refat_plot,
            x="qtd_erros",
            y="taxa_refaturamento_pct",
            size="qtd_erros",
            color="causa_canonica",
            hover_name="causa_canonica",
            title="Volume × taxa de refaturamento",
        )
        render_chart(st, fig, key="impact_refat", theme=theme, on_select="rerun")
        download_dataframe(st, "📥 CSV refaturamento", refat, section="impacto_refaturamento")
    else:
        render_table_or_empty(st, refat, section="impacto_refaturamento")

    left, right = st.columns(2)
    with left:
        if not categories.empty:
            fig = px.bar(
                categories,
                x="categoria",
                y="qtd_erros",
                color="regiao",
                barmode="group",
                title="Impacto por categoria da taxonomia",
            )
            render_chart(st, fig, key="impact_categories", theme=theme, height=380)
            download_dataframe(st, "📥 CSV categorias", categories, section="impacto_categorias")
    with right:
        if not reincidence.empty:
            fig = px.bar(
                reincidence,
                x="faixa",
                y="qtd_instalacoes",
                color="regiao",
                color_discrete_sequence=SEQUENTIAL_ORANGE,
                title="Reincidência por instalação anonimizada",
            )
            render_chart(st, fig, key="impact_reincidence", theme=theme, height=380)
