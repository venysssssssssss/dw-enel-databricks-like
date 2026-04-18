"""Skeleton and loading-state helpers for Streamlit.

The shimmer keyframes and `.enel-skeleton` class are defined in
`apps.streamlit.theme.dashboard_css` so the skeleton inherits the active theme
(light / dark / graphite).  This module only emits theme-aware markup.
"""

from __future__ import annotations

from typing import Any


def skeleton_block(height_px: int = 128) -> str:
    """Return a themed skeleton block.

    The height is inlined so that any caller can size the placeholder without
    adding a new CSS class.  Styling lives in `theme.dashboard_css`.
    """
    return (
        f'<div class="enel-skeleton" role="progressbar" aria-busy="true" '
        f'aria-label="Carregando dados" style="min-height:{height_px}px"></div>'
    )


def render_skeleton(st: Any, *, height_px: int = 128) -> None:  # pragma: no cover
    st.markdown(skeleton_block(height_px), unsafe_allow_html=True)
