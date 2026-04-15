"""Skeleton and loading-state helpers for Streamlit."""

from __future__ import annotations

from typing import Any

SKELETON_CSS = """
<style>
.enel-skeleton {
  min-height: 128px;
  border-radius: 22px;
  background:
    linear-gradient(
      100deg,
      rgba(230,236,242,0.65) 20%,
      rgba(255,255,255,0.95) 40%,
      rgba(230,236,242,0.65) 60%
    );
  background-size: 220% 100%;
  animation: enelShimmer 1.2s ease-in-out infinite;
  border: 1px solid var(--enel-border);
}
@keyframes enelShimmer {
  0% { background-position: 120% 0; }
  100% { background-position: -120% 0; }
}
</style>
"""


def skeleton_block(height_px: int = 128) -> str:
    return f'{SKELETON_CSS}<div class="enel-skeleton" style="min-height:{height_px}px"></div>'


def render_skeleton(st: Any, *, height_px: int = 128) -> None:  # pragma: no cover
    st.markdown(skeleton_block(height_px), unsafe_allow_html=True)
