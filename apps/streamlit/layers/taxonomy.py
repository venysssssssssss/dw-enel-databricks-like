from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd
import plotly.express as px

from apps.streamlit.components.narrative import download_dataframe
from apps.streamlit.components.premium import (
    StoryBlock,
    TopicPill,
    render_story,
    render_topbar,
    topic_pills_markdown,
)
from apps.streamlit.layers.common import render_chart, render_table_or_empty
from apps.streamlit.theme import SEQUENTIAL_GREEN, format_int
from src.viz.erro_leitura_dashboard_data import safe_topic_taxonomy_for_display, taxonomy_reference

if TYPE_CHECKING:
    from pathlib import Path


def render(st: Any, taxonomy_path: Path, *, theme: str = "light") -> None:
    render_topbar(st, crumb="MIS / Taxonomia Descoberta", status="BERTopic v3 · PII-safe")
    render_story(
        st,
        StoryBlock(
            icon="Σ",
            lead="O que a IA descobriu nos textos livres e como conversa com a taxonomia?",
            body=(
                "Tópicos BERTopic <b>mascarados</b>, palavras-chave e exemplos "
                "<b>PII-safe</b>. Use para melhorar rótulos, regras e treinamento."
            ),
        ),
    )
    taxonomy = _read_taxonomy(taxonomy_path)
    safe = safe_topic_taxonomy_for_display(taxonomy) if not taxonomy.empty else pd.DataFrame()

    # Topic pills (top 12 by size) — absorvido do MIS Aconchegante
    if not safe.empty and "topic_size" in safe.columns and "topic_name" in safe.columns:
        top_pills = (
            safe.sort_values("topic_size", ascending=False)
            .head(12)
            .assign(_count=lambda d: d["topic_size"].map(format_int))
        )
        pills = [
            TopicPill(name=str(row["topic_name"]), count=str(row["_count"]))
            for _, row in top_pills.iterrows()
        ]
        st.markdown(
            '<div class="enel-card" style="padding:18px 22px;margin-bottom:16px">'
            '<div style="font-family:var(--font-display);font-weight:700;font-size:17px;'
            'letter-spacing:-0.01em;margin-bottom:4px">Tópicos recorrentes</div>'
            '<div style="font-size:12px;color:var(--text-dim);margin-bottom:12px">'
            "Top 12 por volume · valores são nº de documentos atribuídos</div>"
            + topic_pills_markdown(pills)
            + "</div>",
            unsafe_allow_html=True,
        )

    if not safe.empty and "topic_size" in safe.columns:
        fig = px.bar(
            safe.sort_values("topic_size", ascending=False).head(20),
            x="topic_size",
            y="topic_name",
            orientation="h",
            color="topic_size",
            color_continuous_scale=SEQUENTIAL_GREEN,
            title="Tópicos descobertos por volume",
        )
        fig.update_yaxes(categoryorder="total ascending")
        render_chart(st, fig, key="taxonomy_topics", theme=theme, height=520)
        download_dataframe(st, "📥 CSV tópicos descobertos", safe, section="taxonomia_topicos")

    render_table_or_empty(st, safe, section="taxonomia_descoberta")
    with st.expander("Taxonomia canônica usada pelo classificador"):
        render_table_or_empty(st, taxonomy_reference(), section="taxonomia_canonica")


def _read_taxonomy(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    if path.suffix.lower() == ".json":
        return pd.read_json(path)
    return pd.read_csv(path)
