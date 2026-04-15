from __future__ import annotations

from typing import Any

import plotly.express as px

from apps.streamlit.components.narrative import LayerNarrative, layer_intro
from apps.streamlit.layers.common import aggregate, render_chart, render_table_or_empty
from apps.streamlit.theme import SEQUENTIAL_BLUE, format_int, format_pct
from src.viz.erro_leitura_dashboard_data import severity_heatmap, taxonomy_reference


def render(st: Any, frame, *, theme: str = "light") -> None:
    layer_intro(
        st,
        LayerNarrative(
            icon="🛡",
            title="Governança Analítica",
            question="A base está explicável, rotulada e segura o suficiente para decisão?",
            method=(
                "Cobertura de labels, severidade, anonimização por hash e documentação "
                "da taxonomia."
            ),
            action="Monitore indefinidos, baixa cobertura de causa-raiz e classes críticas.",
        ),
    )
    indef = (
        int(frame["causa_canonica"].eq("indefinido").sum()) if "causa_canonica" in frame else 0
    )
    label_rate = (
        float(frame["has_causa_raiz_label"].mean())
        if "has_causa_raiz_label" in frame
        else 0.0
    )
    hash_rate = float(frame["instalacao_hash"].ne("").mean()) if "instalacao_hash" in frame else 0.0
    cols = st.columns(4)
    cols[0].metric("Registros auditáveis", format_int(len(frame)))
    cols[1].metric("Indefinidos IA", format_int(indef), help="Casos com sinal fraco ou ambíguo.")
    cols[2].metric("Cobertura label origem", format_pct(label_rate))
    cols[3].metric("IDs anonimizados", format_pct(hash_rate))

    severity = aggregate(severity_heatmap, frame)
    if not severity.empty:
        fig = px.density_heatmap(
            severity,
            x="severidade",
            y="regiao",
            z="taxa_refaturamento",
            color_continuous_scale=SEQUENTIAL_BLUE,
            title="Risco de refaturamento por severidade",
        )
        render_chart(st, fig, key="governance_severity", theme=theme, height=360)

    with st.expander("Contrato de segurança e explicabilidade"):
        st.markdown(
            """
- Textos livres não são exibidos brutos no dashboard executivo.
- Instalações são representadas por hash SHA-256 truncado.
- Exemplos de tópicos passam por mascaramento de telefone, e-mail, CEP e protocolo.
- `indefinido` é uma fila de revisão, não uma classe operacional definitiva.
"""
        )
        render_table_or_empty(st, taxonomy_reference(), section="governanca_taxonomia")
