from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd
import plotly.express as px

from apps.streamlit.components.narrative import LayerNarrative, download_dataframe, layer_intro
from apps.streamlit.layers.common import render_chart, render_table_or_empty
from apps.streamlit.theme import SEQUENTIAL_GREEN
from src.viz.erro_leitura_dashboard_data import safe_topic_taxonomy_for_display, taxonomy_reference

if TYPE_CHECKING:
    from pathlib import Path


def render(st: Any, taxonomy_path: Path, *, theme: str = "light") -> None:
    layer_intro(
        st,
        LayerNarrative(
            icon="🧬",
            title="Taxonomia Descoberta",
            question="O que a IA descobriu nos textos livres e como isso conversa com a taxonomia?",
            method="Tópicos BERTopic mascarados, palavras-chave e exemplos PII-safe.",
            action="Use exemplos e keywords para melhorar regras, labels e treinamento.",
        ),
    )
    taxonomy = _read_taxonomy(taxonomy_path)
    safe = safe_topic_taxonomy_for_display(taxonomy) if not taxonomy.empty else pd.DataFrame()
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
