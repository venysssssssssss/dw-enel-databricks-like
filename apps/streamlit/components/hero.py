"""Hero and executive cards for the ENEL Streamlit dashboard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from apps.streamlit.theme import format_int, format_pct
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
  <p style="margin-top:0.85rem;font-weight:700;">
    Escopo filtrado: {format_int(total_filtered)} de {format_int(total_available)} registros
    ({format_pct(coverage)}).
  </p>
</section>
"""


def render_hero(  # pragma: no cover - exercised by Streamlit smoke/e2e.
    st: Any,
    frame: pd.DataFrame,
    *,
    total_available: int,
) -> None:
    st.markdown(
        hero_markdown(total_filtered=len(frame), total_available=total_available),
        unsafe_allow_html=True,
    )
    kpis = compute_kpis(frame)
    cols = st.columns(5)
    cols[0].metric(
        "Registros analisados",
        format_int(kpis.total_registros),
        help="Quantidade de ordens no escopo filtrado atual.",
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
    cols[3].metric(
        "Taxa refaturamento",
        format_pct(kpis.taxa_refaturamento),
        help="Média de `flag_resolvido_com_refaturamento` no escopo filtrado.",
    )
    cols[4].metric(
        "Instalações reincidentes",
        format_int(kpis.instalacoes_reincidentes),
        help="Instalações anonimizadas com mais de uma ordem no período filtrado.",
    )
