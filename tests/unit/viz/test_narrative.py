from __future__ import annotations

import pandas as pd

from apps.streamlit.components.hero import hero_markdown
from apps.streamlit.components.narrative import (
    LayerNarrative,
    build_intro_markdown,
    dataframe_to_csv_bytes,
    empty_state_markdown,
    export_filename,
)
from apps.streamlit.components.skeleton import skeleton_block
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
