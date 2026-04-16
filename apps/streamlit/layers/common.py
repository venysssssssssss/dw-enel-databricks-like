"""Shared helpers for Streamlit dashboard layers."""

from __future__ import annotations

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
        title={
            "font": {"size": 15, "color": template["font"]["color"], "family": "Inter, sans-serif"},
            "x": 0.0,
            "xanchor": "left",
            "pad": {"l": 4, "t": 4},
        },
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


def render_table_or_empty(st: Any, frame: pd.DataFrame, *, section: str) -> None:
    if frame.empty:
        render_empty_state(st)
        return
    st.dataframe(frame, use_container_width=True, hide_index=True)
    download_dataframe(st, "📥 CSV desta seção", frame, section=section)


def color_sequence() -> list[str]:
    return CATEGORICAL_SEQUENCE
