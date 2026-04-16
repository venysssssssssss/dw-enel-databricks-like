"""Small TypeScript/React island embedded inside the Streamlit dashboard."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.viz.erro_leitura_dashboard_data import compute_kpis, root_cause_distribution

ASSET_PATH = Path(__file__).resolve().parents[1] / "static" / "enel_streamlit_island.js"


def render_react_island(
    st: Any,
    frame: pd.DataFrame,
    *,
    total_available: int,
    dataset_hash: str,
    theme: str,
) -> None:
    """Render the compiled React island inline, with an HTML fallback when absent."""
    props = _props(
        frame,
        total_available=total_available,
        dataset_hash=dataset_hash,
        theme=theme,
    )
    if not ASSET_PATH.exists():
        st.markdown(_fallback_html(props), unsafe_allow_html=True)
        return

    import streamlit.components.v1 as components

    script = ASSET_PATH.read_text(encoding="utf-8")
    payload = json.dumps(props, ensure_ascii=False)
    components.html(
        f"""
        <div id="enel-streamlit-island"></div>
        <script id="enel-streamlit-island-data" type="application/json">
        {html.escape(payload)}
        </script>
        <script>{script}</script>
        """,
        height=252,
        scrolling=False,
    )


def _props(
    frame: pd.DataFrame,
    *,
    total_available: int,
    dataset_hash: str,
    theme: str,
) -> dict[str, Any]:
    kpis = compute_kpis(frame)
    causes = root_cause_distribution(frame, limit=1)
    top_cause = "" if causes.empty else str(causes["causa_canonica"].iloc[0])
    regions = sorted(
        frame.get("regiao", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
    )
    return {
        "theme": "dark" if theme == "dark" else "light",
        "datasetHash": dataset_hash,
        "totalFiltered": int(kpis.total_registros),
        "totalAvailable": int(total_available),
        "refaturamentoRate": float(kpis.taxa_refaturamento),
        "labelRate": float(kpis.taxa_rotulo_origem),
        "regions": regions,
        "topCause": top_cause,
    }


def _fallback_html(props: dict[str, Any]) -> str:
    coverage = props["totalFiltered"] / props["totalAvailable"] if props["totalAvailable"] else 0.0
    return f"""
    <section class="enel-card enel-ts-fallback" aria-label="Painel TypeScript pendente">
      <strong>Pulso operacional</strong>
      <p>
        Bundle TypeScript ainda não compilado. O dashboard segue operacional com
        {props["totalFiltered"]:,} ordens filtradas ({coverage:.1%} do total).
      </p>
    </section>
    """
