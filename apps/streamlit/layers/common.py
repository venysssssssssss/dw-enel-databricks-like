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
    fig.update_layout(**plotly_template("dark" if theme == "dark" else "light"), height=height)
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
