from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from apps.streamlit.components.hero import hero_markdown
from apps.streamlit.components.narrative import (
    LayerNarrative,
    build_intro_markdown,
    dataframe_to_csv_bytes,
    empty_state_markdown,
    export_filename,
)
from apps.streamlit.components.skeleton import skeleton_block
from apps.streamlit.layers.common import (
    apply_layout,
    assistant_cta_markdown,
    chart_section_markdown,
)
from apps.streamlit.theme import (
    css_variables,
    dashboard_css,
    format_int,
    format_pct,
    plotly_template,
)


def test_build_intro_markdown_contains_story_contract() -> None:
    html = build_intro_markdown(
        LayerNarrative(
            title="Ritmo",
            question="O que subiu?",
            method="Série temporal",
            action="Filtrar CE",
            icon="📈",
        )
    )

    assert "Pergunta de negócio" in html
    assert "Como lemos" in html
    assert "Próximo passo" in html
    assert "Ritmo" in html
    assert "enel-tab-header" in html


def test_chart_section_markdown_keeps_title_outside_plotly() -> None:
    html = chart_section_markdown(
        title="Volume mensal",
        subtitle="Série no escopo filtrado",
        badge="linha",
    )

    assert "enel-chart-section" in html
    assert "<h2>Volume mensal</h2>" in html
    assert "Série no escopo filtrado" in html
    assert "linha" in html


def test_apply_layout_overrides_template_margin_once() -> None:
    fig = apply_layout(go.Figure(), height=320)

    assert fig.layout.height == 320
    assert fig.layout.title.text is None
    assert fig.layout.margin.t == 24


def test_assistant_cta_markdown_carries_context() -> None:
    html = assistant_cta_markdown("Ritmo")

    assert "Assistente contextual" in html
    assert "Ritmo" in html


def test_empty_state_markdown_is_status_block() -> None:
    html = empty_state_markdown(title="Sem dados", detail="Troque o filtro")

    assert "role=\"status\"" in html
    assert "Sem dados" in html
    assert "Troque o filtro" in html


def test_dataframe_to_csv_bytes_is_excel_friendly() -> None:
    payload = dataframe_to_csv_bytes(pd.DataFrame({"col": ["ação"]}))

    assert payload.startswith(b"\xef\xbb\xbf")
    assert "ação".encode() in payload


def test_export_filename_sanitizes_section() -> None:
    name = export_filename("CE · Macro Temas")

    assert name.startswith("enel_ce___macro_temas_")
    assert name.endswith(".csv")


def test_theme_helpers_return_accessible_assets() -> None:
    css = dashboard_css("dark")
    template = plotly_template("dark")

    assert "--enel-bg" in css
    assert "oklch" in css_variables("light")["--enel-surface"]
    assert "Inter" in css
    assert template["paper_bgcolor"] == "rgba(0,0,0,0)"
    assert format_int(12345) == "12.345"
    assert format_pct(0.1234) == "12.3%"


def test_hero_markdown_handles_zero_total() -> None:
    html = hero_markdown(total_filtered=5, total_available=0)

    assert "Reclamações CE/SP em análise" in html
    assert "(0.0%)" in html


def test_skeleton_block_sets_height() -> None:
    assert "min-height:240px" in skeleton_block(240)
