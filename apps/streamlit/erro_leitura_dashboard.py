"""Streamlit entrypoint for ENEL erro de leitura intelligence dashboard."""

# ruff: noqa: E402

from __future__ import annotations

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
from apps.streamlit.components.narrative import render_empty_state
from apps.streamlit.components.sidebar import (
    clean_tab_label,
    render_sidebar_brand,
    render_sidebar_section,
)
from apps.streamlit.components.skeleton import render_skeleton
from apps.streamlit.theme import dashboard_css

TAB_LABELS = [
    "BI MIS Executivo",
    "CE Totais",
    "Ritmo",
    "Padrões",
    "Impacto",
    "Taxonomia",
    "Governança",
    "Sessão Educacional",
    "Assistente",
]


def main() -> None:
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
    from src.viz.cache import path_fingerprint

    st.set_page_config(
        page_title="Erros de Leitura | Inteligência Operacional ENEL",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.markdown(render_sidebar_brand(version_label="BI · silver"), unsafe_allow_html=True)
    st.sidebar.markdown(
        render_sidebar_section("Navegação", badge=str(len(TAB_LABELS))),
        unsafe_allow_html=True,
    )
    pending_tab = st.session_state.pop("dashboard_pending_tab", None)
    if pending_tab in TAB_LABELS:
        st.session_state["dashboard_active_tab"] = pending_tab
    if st.session_state.get("dashboard_active_tab") not in {None, *TAB_LABELS}:
        st.session_state["dashboard_active_tab"] = TAB_LABELS[0]
    active_tab = st.sidebar.radio(
        "Navegação",
        options=TAB_LABELS,
        index=0,
        format_func=clean_tab_label,
        label_visibility="collapsed",
        key="dashboard_active_tab",
    )

    st.sidebar.markdown(
        render_sidebar_section("Global", badge="fontes + filtros"),
        unsafe_allow_html=True,
    )
    _render_onboarding_controls()

    silver_path, assignments_path, taxonomy_path = _render_source_controls()
    st.sidebar.markdown(
        render_sidebar_section("Escopo", badge="CE + SP"),
        unsafe_allow_html=True,
    )
    include_total = st.sidebar.toggle(
        "Incluir reclamação_total",
        value=_query_bool("total"),
        help=(
            "Por padrão o dashboard considera apenas erros de leitura CE e Base N1 SP. "
            "Ative para cruzar com reclamações totais."
        ),
    )

    st.markdown(dashboard_css("light"), unsafe_allow_html=True)
    skeleton_slot = st.empty()
    with skeleton_slot.container():
        render_skeleton(st, height_px=96)
    with st.spinner("Preparando dados analíticos..."):
        frame = _load_frame(
            str(silver_path),
            str(assignments_path),
            str(taxonomy_path),
            include_total,
            path_fingerprint(silver_path),
            path_fingerprint(assignments_path),
            path_fingerprint(taxonomy_path),
        )
    skeleton_slot.empty()

    if frame.empty:
        render_empty_state(
            st,
            title="Nenhum registro disponível",
            detail="Verifique os caminhos de dados na barra lateral.",
        )
        return

    filters = render_sidebar_filters(st, frame, include_total=include_total)
    if filters.theme == "dark":
        st.markdown(dashboard_css("dark"), unsafe_allow_html=True)
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

    theme = filters.theme
    context_hint = st.session_state.get("last_dashboard_area")

    if active_tab == TAB_LABELS[0]:
        st.session_state["last_dashboard_area"] = "BI MIS Executivo"
        mis.render(st, filtered, theme=theme, total_available=len(frame))
    elif active_tab == TAB_LABELS[1]:
        st.session_state["last_dashboard_area"] = "CE Totais"
        reclamacoes_ce.render(st, silver_path=silver_path, erro_leitura_frame=frame, theme=theme)
    elif active_tab == TAB_LABELS[2]:
        st.session_state["last_dashboard_area"] = "Ritmo"
        executive.render(st, filtered, theme=theme)
    elif active_tab == TAB_LABELS[3]:
        st.session_state["last_dashboard_area"] = "Padrões"
        patterns.render(st, filtered, theme=theme)
    elif active_tab == TAB_LABELS[4]:
        st.session_state["last_dashboard_area"] = "Impacto"
        impact.render(st, filtered, theme=theme)
    elif active_tab == TAB_LABELS[5]:
        st.session_state["last_dashboard_area"] = "Taxonomia"
        taxonomy_layer.render(st, taxonomy_path, theme=theme)
    elif active_tab == TAB_LABELS[6]:
        st.session_state["last_dashboard_area"] = "Governança"
        governance.render(st, filtered, theme=theme)
    elif active_tab == TAB_LABELS[7]:
        st.session_state["last_dashboard_area"] = "Sessão Educacional"
        educational.render(st, theme=theme)
    elif active_tab == TAB_LABELS[8]:
        chat.render(st, theme=theme, context_hint=context_hint)


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
    from src.viz.erro_leitura_dashboard_data import load_dashboard_frame

    del silver_sig, assignments_sig, taxonomy_sig
    return load_dashboard_frame(
        silver_path=Path(silver_path),
        topic_assignments_path=Path(assignments_path),
        topic_taxonomy_path=Path(taxonomy_path),
        include_total=include_total,
    )


def _render_source_controls() -> tuple[Path, Path, Path]:
    from src.viz.erro_leitura_dashboard_data import (
        DEFAULT_SILVER_PATH,
        DEFAULT_TOPIC_ASSIGNMENTS_PATH,
        DEFAULT_TOPIC_TAXONOMY_PATH,
    )

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
    st.sidebar.markdown(
        """
<div class="sb-mini-note">
  Tour curto no primeiro acesso: hero → filtros → abas → Sprint 15/chat.
</div>
""",
        unsafe_allow_html=True,
    )


def _render_tour(st_module) -> None:
    if st_module.session_state.get("dashboard_tour_seen"):
        return
    st_module.toast("1/4 BI MIS: comece pelo escopo e KPIs executivos.", icon="⚡")
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
