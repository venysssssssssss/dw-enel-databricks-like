"""Hero and executive cards for the ENEL Streamlit dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.streamlit.theme import (
    PALETTE,
    format_int,
    format_pct,
    plotly_template,
)
from src.viz.erro_leitura_dashboard_data import compute_kpis

if TYPE_CHECKING:
    import pandas as pd


def hero_markdown(*, total_filtered: int, total_available: int) -> str:
    coverage = total_filtered / total_available if total_available else 0.0
    return f"""
<section class="enel-hero" aria-label="Resumo executivo do dashboard">
  <h1>Inteligência operacional de leitura</h1>
  <p>
    IA, taxonomia viva e reclamações CE/SP em uma única narrativa: do volume ao padrão,
    do padrão ao impacto, do impacto à ação operacional.
  </p>
  <span class="enel-hero-meta" aria-live="polite">
    📊 Escopo: {format_int(total_filtered)} de
    {format_int(total_available)} ({format_pct(coverage)})
  </span>
</section>
"""


def render_hero(  # pragma: no cover - exercised by Streamlit smoke/e2e.
    st: Any,
    frame: pd.DataFrame,
    *,
    total_available: int,
    baseline_kpis: Any | None = None,
) -> None:
    st.markdown(
        hero_markdown(total_filtered=len(frame), total_available=total_available),
        unsafe_allow_html=True,
    )
    kpis = compute_kpis(frame)
    coverage = kpis.total_registros / total_available if total_available else 0.0

    cols = st.columns(5)
    cols[0].metric(
        "Registros analisados",
        format_int(kpis.total_registros),
        delta=f"{format_pct(coverage)} do total",
        delta_color="off",
        help="Quantidade de ordens no escopo filtrado atual vs total disponível.",
    )
    cols[1].metric(
        "Regiões",
        format_int(kpis.regioes),
        help="Número de regiões presentes após filtros.",
    )
    cols[2].metric(
        "Tópicos IA",
        format_int(kpis.topicos),
        help="Tópicos BERTopic distintos no escopo atual.",
    )

    refat_delta: str | None = None
    refat_delta_color: str = "off"
    if baseline_kpis is not None and getattr(baseline_kpis, "taxa_refaturamento", None):
        diff = kpis.taxa_refaturamento - baseline_kpis.taxa_refaturamento
        if abs(diff) >= 0.001:
            sign = "+" if diff > 0 else ""
            refat_delta = f"{sign}{diff * 100:.1f} pp vs base"
            refat_delta_color = "inverse"  # menor refaturamento é melhor
    cols[3].metric(
        "Taxa refaturamento",
        format_pct(kpis.taxa_refaturamento),
        delta=refat_delta,
        delta_color=refat_delta_color,
        help="Média de `flag_resolvido_com_refaturamento` no escopo filtrado.",
    )
    cols[4].metric(
        "Instalações reincidentes",
        format_int(kpis.instalacoes_reincidentes),
        help="Instalações anonimizadas com mais de uma ordem no período filtrado.",
    )

    _render_volume_sparkline(st, frame)


def _render_volume_sparkline(st: Any, frame: pd.DataFrame) -> None:
    """Sparkline mensal de volume — contexto temporal sem ocupar espaço."""
    if frame.empty or "data_ingresso" not in frame.columns:
        return
    try:
        import pandas as pd  # local import: heavy dependency only when rendering
        import plotly.graph_objects as go
    except ImportError:
        return

    series = pd.to_datetime(frame["data_ingresso"], errors="coerce").dropna()
    if series.empty:
        return
    monthly = (
        series.dt.to_period("M")
        .value_counts()
        .sort_index()
        .rename_axis("mes")
        .reset_index(name="qtd")
    )
    if len(monthly) < 2:
        return
    monthly["mes_ts"] = monthly["mes"].dt.to_timestamp()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=monthly["mes_ts"],
            y=monthly["qtd"],
            mode="lines+markers",
            line={"color": PALETTE["primary"], "width": 2.5, "shape": "spline"},
            marker={"size": 5, "color": PALETTE["accent"]},
            fill="tozeroy",
            fillcolor="rgba(15, 76, 129, 0.08)",
            hovertemplate="<b>%{x|%b/%Y}</b><br>%{y:,d} ordens<extra></extra>",
            name="Volume",
        )
    )
    template = plotly_template()
    fig.update_layout(
        height=110,
        margin={"l": 12, "r": 12, "t": 8, "b": 12},
        showlegend=False,
        xaxis={
            "showgrid": False,
            "showticklabels": True,
            "tickformat": "%b/%y",
            "tickfont": {"size": 10, "color": template["font"]["color"]},
        },
        yaxis={"visible": False},
        paper_bgcolor=template["paper_bgcolor"],
        plot_bgcolor=template["plot_bgcolor"],
        font=template["font"],
        hoverlabel=template["hoverlabel"],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
