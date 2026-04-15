from __future__ import annotations

from apps.streamlit.erro_leitura_dashboard import TAB_LABELS


def test_dashboard_preserves_sprint_13_tab_order() -> None:
    assert TAB_LABELS == [
        "🧭 BI MIS Executivo",
        "🟧 CE · Reclamacoes Totais",
        "📈 Ritmo Operacional",
        "🗺 Padroes & Concentracoes",
        "💰 Impacto de Refaturamento",
        "🧬 Taxonomia Descoberta",
        "🛡 Governanca",
        "🎓 Sessao Educacional",
    ]
