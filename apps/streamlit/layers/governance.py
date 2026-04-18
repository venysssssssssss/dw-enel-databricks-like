from __future__ import annotations

from typing import Any

import plotly.express as px

from apps.streamlit.components.premium import (
    HealthCard,
    StoryBlock,
    health_grid_markdown,
    render_story,
    render_topbar,
)
from apps.streamlit.layers.common import aggregate, render_chart, render_table_or_empty
from apps.streamlit.theme import SEQUENTIAL_BLUE, format_int, format_pct
from src.viz.erro_leitura_dashboard_data import severity_heatmap, taxonomy_reference


def render(st: Any, frame, *, theme: str = "light") -> None:
    render_topbar(st, crumb="MIS / Governança Analítica", status="Contratos de segurança OK")
    render_story(
        st,
        StoryBlock(
            icon="◆",
            lead="A base está explicável, rotulada e segura o suficiente para decisão?",
            body=(
                "Cobertura de labels, severidade, anonimização por hash e documentação "
                "da taxonomia. Monitore <b>indefinidos</b>, <b>baixa cobertura</b> de "
                "causa-raiz e <b>classes críticas</b>."
            ),
        ),
    )

    indef = (
        int(frame["causa_canonica"].eq("indefinido").sum())
        if "causa_canonica" in frame
        else 0
    )
    label_rate = (
        float(frame["has_causa_raiz_label"].mean())
        if "has_causa_raiz_label" in frame
        else 0.0
    )
    hash_rate = (
        float(frame["instalacao_hash"].ne("").mean())
        if "instalacao_hash" in frame
        else 0.0
    )
    indef_share = indef / max(len(frame), 1)

    cards = [
        HealthCard(
            label="Registros auditáveis",
            value=format_int(len(frame)),
            sub="100% com audit log",
            status="ok",
        ),
        HealthCard(
            label="Indefinidos IA",
            value=format_int(indef),
            sub=f"{format_pct(indef_share)} da base · SLA ≤ 15%",
            status="warn" if indef_share > 0.15 else "ok",
        ),
        HealthCard(
            label="Cobertura label origem",
            value=format_pct(label_rate),
            sub="meta trimestral: 50%",
            status="crit" if label_rate < 0.30 else ("warn" if label_rate < 0.50 else "ok"),
        ),
        HealthCard(
            label="IDs anonimizados",
            value=format_pct(hash_rate),
            sub="LGPD · hash SHA-256",
            status="ok" if hash_rate >= 0.95 else "warn",
        ),
    ]
    st.markdown(health_grid_markdown(cards), unsafe_allow_html=True)

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
        st.markdown(
            '<div class="enel-insight"><span class="label">Leitura</span>'
            "Células escuras = <b>taxa média de refaturamento</b> mais alta. "
            "Use para priorizar revisão de causa-raiz por severidade × região.</div>",
            unsafe_allow_html=True,
        )

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
