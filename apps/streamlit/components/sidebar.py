"""Sidebar shell helpers for the Streamlit MIS dashboard."""

from __future__ import annotations

import html
import re

_ACCENT_FIXES = {
    "Reclamacoes": "Reclamações",
    "Padroes": "Padrões",
    "Concentracoes": "Concentrações",
    "Governanca": "Governança",
    "Sessao": "Sessão",
}


def clean_tab_label(label: str) -> str:
    """Return a display-only label without leading icon glyphs."""
    cleaned = re.sub(r"^[^\wÀ-ÿ]+", "", label).strip()
    for source, target in _ACCENT_FIXES.items():
        cleaned = cleaned.replace(source, target)
    return cleaned


def render_sidebar_brand(total_rows: int | None = None, version_label: str = "BI · silver") -> str:
    """Render the compact MIS brand block used at the top of the sidebar."""
    rows = ""
    if total_rows is not None:
        rows_fmt = f"{total_rows:,}".replace(",", ".")
        rows = f"<span>{rows_fmt} registros</span>"
    return f"""
<div class="sb-brand sb-mis-brand">
  <div class="sb-brand-mark" aria-hidden="true">m</div>
  <div class="sb-brand-text">
    <div class="sb-brand-name">MIS Aconchegante</div>
    <div class="sb-brand-sub">
      <span>{html.escape(version_label)}</span>
      {rows}
    </div>
  </div>
</div>
"""


def render_sidebar_section(title: str, badge: str | None = None, link: str | None = None) -> str:
    """Render a sidebar section heading with optional right-side metadata."""
    if badge is not None:
        right = f'<span class="sb-section-badge">{html.escape(badge)}</span>'
    elif link is not None:
        right = f'<span class="sb-section-link">{html.escape(link)}</span>'
    else:
        right = ""
    return f"""
<div class="sb-section">
  <div class="sb-section-title">{html.escape(title)}</div>
  {right}
</div>
"""


def render_filter_metric(label: str, value: str | int) -> str:
    """Render a compact sidebar metric row for summaries and footers."""
    return (
        "<div class='sb-filter-metric'>"
        f"<span>{html.escape(label)}</span>"
        f"<b>{html.escape(str(value))}</b>"
        "</div>"
    )
