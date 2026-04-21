from __future__ import annotations

from apps.streamlit.erro_leitura_dashboard import TAB_LABELS


def test_dashboard_preserves_current_tab_order() -> None:
    assert TAB_LABELS == [
        "BI MIS Executivo",
        "CE Totais",
        "Ritmo",
        "Padrões",
        "Impacto",
        "Taxonomia",
        "Governança",
        "Sessão Educacional",
        "Assistente",
    ]
