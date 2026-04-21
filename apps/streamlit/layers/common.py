"""Shared helpers for Streamlit dashboard layers."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, Any

from apps.streamlit.components.narrative import download_dataframe, render_empty_state
from apps.streamlit.theme import CATEGORICAL_SEQUENCE, plotly_template
from src.viz.cache import cached_aggregation

if TYPE_CHECKING:
    from collections.abc import Callable

    import pandas as pd


def aggregate(
    func: Callable[..., pd.DataFrame],
    frame: pd.DataFrame,
    **kwargs: Any,
) -> pd.DataFrame:
    return cached_aggregation(func, frame, **kwargs)


def apply_layout(fig: Any, *, theme: str = "light", height: int = 420) -> Any:
    """Aplica template + defaults profissionais (grid suave, hover, tipografia)."""
    is_dark = theme == "dark"
    template = plotly_template("dark" if is_dark else "light")
    grid_color = "rgba(244, 248, 252, 0.06)" if is_dark else "rgba(15, 76, 129, 0.06)"
    axis_color = "#A9B8C8" if is_dark else "#596879"
    fig.update_layout(
        **template,
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 12, "color": template["font"]["color"]},
            "bgcolor": "rgba(0,0,0,0)",
        },
        title_text=None,
        margin={"l": 8, "r": 16, "t": 24, "b": 36},
        separators=",.",  # PT-BR: vírgula decimal, ponto milhar
    )
    fig.update_xaxes(
        gridcolor=grid_color,
        zeroline=False,
        linecolor=grid_color,
        tickfont={"size": 11, "color": axis_color},
        title_font={"size": 12, "color": axis_color},
        ticks="outside",
        tickcolor=grid_color,
    )
    fig.update_yaxes(
        gridcolor=grid_color,
        zeroline=False,
        linecolor=grid_color,
        tickfont={"size": 11, "color": axis_color},
        title_font={"size": 12, "color": axis_color},
    )
    return fig


def chart_section_markdown(
    *,
    title: str,
    subtitle: str = "",
    badge: str = "",
) -> str:
    subtitle_html = f'<p>{escape(subtitle)}</p>' if subtitle else ""
    badge_html = f'<span>{escape(badge)}</span>' if badge else ""
    return (
        '<section class="enel-chart-section" aria-label="'
        f'{escape(title)}">'
        '<div class="enel-chart-head">'
        "<div>"
        f"<h2>{escape(title)}</h2>"
        f"{subtitle_html}"
        "</div>"
        f"{badge_html}"
        "</div>"
        "</section>"
    )


def render_chart(
    st: Any,
    fig: Any,
    *,
    key: str,
    theme: str = "light",
    height: int = 420,
    on_select: str | None = None,
) -> Any:
    apply_layout(fig, theme=theme, height=height)
    fig.update_layout(title_text=None)
    kwargs: dict[str, Any] = {
        "use_container_width": True,
        "key": key,
        "on_select": on_select or "ignore",
        "config": {
            "displaylogo": False,
            "displayModeBar": "hover",
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
            "toImageButtonOptions": {"format": "png", "scale": 2, "filename": key},
        },
    }
    if on_select:
        kwargs["selection_mode"] = ("points", "box", "lasso")
    return st.plotly_chart(fig, **kwargs)


def render_chart_section(
    st: Any,
    fig: Any,
    *,
    key: str,
    title: str,
    subtitle: str = "",
    badge: str = "",
    theme: str = "light",
    height: int = 420,
    on_select: str | None = None,
) -> Any:
    st.markdown(
        chart_section_markdown(title=title, subtitle=subtitle, badge=badge),
        unsafe_allow_html=True,
    )
    return render_chart(
        st,
        fig,
        key=key,
        theme=theme,
        height=height,
        on_select=on_select,
    )


def assistant_cta_markdown(area: str) -> str:
    return (
        '<div class="enel-assistant-cta" role="note">'
        "<div>"
        "<b>Assistente contextual</b>"
        f"<span>Levar o contexto de {escape(area)} para uma pergunta guiada.</span>"
        "</div>"
        "</div>"
    )


def render_assistant_cta(
    st: Any,
    *,
    area: str,
    key: str,
    assistant_tab_label: str = "Assistente",
) -> None:
    st.markdown(assistant_cta_markdown(area), unsafe_allow_html=True)
    if st.button(
        "Abrir assistente com este contexto",
        key=key,
        use_container_width=True,
    ):
        st.session_state["last_dashboard_area"] = area
        st.session_state["dashboard_pending_tab"] = assistant_tab_label
        st.rerun()


def render_table_or_empty(st: Any, frame: pd.DataFrame, *, section: str) -> None:
    if frame.empty:
        render_empty_state(st)
        return
    st.dataframe(frame, use_container_width=True, hide_index=True)
    download_dataframe(st, "📥 CSV desta seção", frame, section=section)


def color_sequence() -> list[str]:
    return CATEGORICAL_SEQUENCE
