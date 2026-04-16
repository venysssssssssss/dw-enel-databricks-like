"""Streamlit entrypoint for ENEL erro de leitura intelligence dashboard."""

# ruff: noqa: E402

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - runtime guidance for optional UI deps.
    raise SystemExit(
        f"Dependência visual ausente: {exc.name}. Instale com: .venv/bin/pip install -e '.[viz]'"
    ) from exc

from apps.streamlit.components.filters import (
    active_filter_chips,
    apply_dashboard_filters,
    filter_options,
    render_sidebar_filters,
)
from apps.streamlit.components.hero import render_hero
from apps.streamlit.components.narrative import render_empty_state
from apps.streamlit.components.skeleton import render_skeleton
from apps.streamlit.layers import (
    chat,
    educational,
    executive,
    governance,
    impact,
    mis,
    patterns,
    reclamacoes_ce,
)
from apps.streamlit.layers import taxonomy as taxonomy_layer
from apps.streamlit.theme import dashboard_css
from src.viz.cache import path_fingerprint
from src.viz.erro_leitura_dashboard_data import (
    DEFAULT_SILVER_PATH,
    DEFAULT_TOPIC_ASSIGNMENTS_PATH,
    DEFAULT_TOPIC_TAXONOMY_PATH,
    load_dashboard_frame,
)

TAB_LABELS = [
    "💬 Assistente ENEL",
    "🧭 BI MIS Executivo",
    "🟧 CE · Reclamacoes Totais",
    "📈 Ritmo Operacional",
    "🗺 Padroes & Concentracoes",
    "💰 Impacto de Refaturamento",
    "🧬 Taxonomia Descoberta",
    "🛡 Governanca",
    "🎓 Sessao Educacional",
]


def main() -> None:
    st.set_page_config(
        page_title="Erros de Leitura | Inteligência Operacional ENEL",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    if os.getenv("ENEL_UI", "streamlit").strip().lower() == "react":
        target = os.getenv("ENEL_WEB_URL", "http://localhost:5173")
        st.info("A interface React está ativa para este ambiente.")
        st.link_button("Abrir SPA ENEL", target, use_container_width=True)
        st.stop()

    st.sidebar.title("⚙ Controles")
    st.sidebar.caption("Fontes, filtros e experiência")
    _render_onboarding_controls()

    silver_path, assignments_path, taxonomy_path = _render_source_controls()
    include_total = st.sidebar.toggle(
        "Incluir reclamação_total",
        value=_query_bool("total"),
        help=(
            "Por padrão o dashboard considera apenas erros de leitura CE e Base N1 SP. "
            "Ative para cruzar com reclamações totais."
        ),
    )

    with st.spinner("Preparando dados analíticos..."):
        render_skeleton(st, height_px=96)
        frame = _load_frame(
            str(silver_path),
            str(assignments_path),
            str(taxonomy_path),
            include_total,
            path_fingerprint(silver_path),
            path_fingerprint(assignments_path),
            path_fingerprint(taxonomy_path),
        )

    if frame.empty:
        st.markdown(dashboard_css("light"), unsafe_allow_html=True)
        render_empty_state(
            st,
            title="Nenhum registro disponível",
            detail="Verifique os caminhos de dados na barra lateral.",
        )
        return

    filters = render_sidebar_filters(st, frame, include_total=include_total)
    st.markdown(
        dashboard_css("dark" if filters.theme == "dark" else "light"),
        unsafe_allow_html=True,
    )
    filtered = apply_dashboard_filters(frame, filters)
    _render_tour(st)

    if filtered.empty:
        render_empty_state(
            st,
            title="Nenhum registro para estes filtros",
            detail="Use os presets da barra lateral ou limpe filtros restritivos.",
        )
        return

    options = filter_options(frame)
    st.markdown(
        "<div aria-label='Filtros ativos'>"
        + "".join(
            f"<span class='enel-chip'>{chip}</span>"
            for chip in active_filter_chips(filters, options)
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    render_hero(st, filtered, total_available=len(frame))

    tabs = st.tabs(TAB_LABELS)
    theme = filters.theme
    context_hint = st.session_state.get("last_dashboard_area")
    with tabs[0]:
        chat.render(st, theme=theme, context_hint=context_hint)
    with tabs[1]:
        st.session_state["last_dashboard_area"] = "BI MIS Executivo"
        mis.render(st, filtered, theme=theme)
    with tabs[2]:
        st.session_state["last_dashboard_area"] = "CE · Reclamações Totais"
        reclamacoes_ce.render(st, silver_path=silver_path, erro_leitura_frame=frame, theme=theme)
    with tabs[3]:
        executive.render(st, filtered, theme=theme)
    with tabs[4]:
        patterns.render(st, filtered, theme=theme)
    with tabs[5]:
        impact.render(st, filtered, theme=theme)
    with tabs[6]:
        taxonomy_layer.render(st, taxonomy_path, theme=theme)
    with tabs[7]:
        governance.render(st, filtered, theme=theme)
    with tabs[8]:
        educational.render(st, theme=theme)


@st.cache_data(show_spinner=False)
def _load_frame(
    silver_path: str,
    assignments_path: str,
    taxonomy_path: str,
    include_total: bool,
    silver_sig: str,
    assignments_sig: str,
    taxonomy_sig: str,
):
    """Load dashboard data with explicit file signatures for cache invalidation."""
    del silver_sig, assignments_sig, taxonomy_sig
    return load_dashboard_frame(
        silver_path=Path(silver_path),
        topic_assignments_path=Path(assignments_path),
        topic_taxonomy_path=Path(taxonomy_path),
        include_total=include_total,
    )


def _render_source_controls() -> tuple[Path, Path, Path]:
    with st.sidebar.expander("Fontes de dados", expanded=False):
        silver_path = Path(st.text_input("Dataset Silver", str(DEFAULT_SILVER_PATH)))
        assignments_path = Path(
            st.text_input("Topic assignments", str(DEFAULT_TOPIC_ASSIGNMENTS_PATH))
        )
        taxonomy_path = Path(st.text_input("Taxonomia", str(DEFAULT_TOPIC_TAXONOMY_PATH)))
    return silver_path, assignments_path, taxonomy_path


def _render_onboarding_controls() -> None:
    if st.sidebar.button("Ver tour de novo", use_container_width=True):
        st.session_state["dashboard_tour_seen"] = False
    st.sidebar.caption("Tour curto no primeiro acesso: hero → filtros → abas → Sprint 15/chat.")


def _render_tour(st_module) -> None:
    if st_module.session_state.get("dashboard_tour_seen"):
        return
    st_module.toast("1/4 Hero: comece pelo escopo e KPIs executivos.", icon="⚡")
    st_module.toast("2/4 Filtros: ficam persistidos entre abas e na URL.", icon="🎛")
    st_module.toast("3/4 Abas: cada camada explica pergunta, método e próximo passo.", icon="🧭")
    st_module.toast("4/4 Sprint 15: este layout já prepara o futuro chat RAG.", icon="💬")
    st_module.session_state["dashboard_tour_seen"] = True


def _query_bool(key: str) -> bool:
    value = st.query_params.get(key, "0")
    if isinstance(value, list):
        value = value[0] if value else "0"
    return str(value) == "1"


if __name__ == "__main__":
    main()
