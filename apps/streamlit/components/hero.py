"""Hero and executive cards for the ENEL Streamlit dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.streamlit.components.premium import KPI, kpi_strip_markdown
from apps.streamlit.theme import (
    PALETTE,
    format_int,
    format_pct,
    plotly_template,
)

if TYPE_CHECKING:
    import pandas as pd


def hero_markdown(*, total_filtered: int, total_available: int) -> str:
    coverage = total_filtered / total_available if total_available else 0.0
    return f"""
<section class="enel-hero" aria-label="Resumo executivo do dashboard">
  <h1>Reclamações CE/SP em análise</h1>
  <p>
    Base filtrada, métricas operacionais e assistente RAG no mesmo fluxo de investigação.
    Ajuste o escopo na lateral e acompanhe os impactos nos indicadores.
  </p>
  <span class="enel-hero-meta" aria-live="polite">
    Escopo ativo: {format_int(total_filtered)} de
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
    from src.viz.erro_leitura_dashboard_data import compute_kpis

    st.markdown(
        hero_markdown(total_filtered=len(frame), total_available=total_available),
        unsafe_allow_html=True,
    )
    kpis = compute_kpis(frame)
    coverage = kpis.total_registros / total_available if total_available else 0.0

    refat_delta: str | None = None
    refat_intent = "neutral"
    if baseline_kpis is not None and getattr(baseline_kpis, "taxa_refaturamento", None):
        diff = kpis.taxa_refaturamento - baseline_kpis.taxa_refaturamento
        if abs(diff) >= 0.001:
            sign = "+" if diff > 0 else ""
            refat_delta = f"{sign}{diff * 100:.1f} pp vs base"
            refat_intent = "up_bad" if diff > 0 else "down_good"
    st.markdown(
        kpi_strip_markdown(
            [
                KPI(
                    "Registros analisados",
                    format_int(kpis.total_registros),
                    tag="escopo",
                    delta=f"{format_pct(coverage)} do total",
                    dominant=True,
                ),
                KPI("Regiões", format_int(kpis.regioes), tag="ativas"),
                KPI("Tópicos IA", format_int(kpis.topicos), tag="BERTopic"),
                KPI(
                    "Taxa refaturamento",
                    format_pct(kpis.taxa_refaturamento),
                    tag="média",
                    delta=refat_delta or "escopo atual",
                    delta_intent=refat_intent,
                ),
                KPI(
                    "Instalações reincidentes",
                    format_int(kpis.instalacoes_reincidentes),
                    tag="≥ 2 ordens",
                ),
            ]
        ),
        unsafe_allow_html=True,
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
