from __future__ import annotations

from pathlib import Path

import pytest

from src.ingestion.descricoes_enel_ingestor import read_excel_directory
from src.transformation.processors.erro_leitura_normalizer import normalize_erro_leitura_frame


@pytest.mark.skipif(
    not Path("DESCRICOES_ENEL").exists(),
    reason="DESCRICOES_ENEL nao esta disponivel neste ambiente.",
)
def test_erro_leitura_excel_to_silver_smoke() -> None:
    raw_frame, summaries = read_excel_directory(Path("DESCRICOES_ENEL"))
    normalized = normalize_erro_leitura_frame(raw_frame)

    assert len(summaries) >= 1
    assert {"CE", "SP"}.intersection(set(raw_frame["_source_region"]))
    assert {"ordem", "texto_completo", "has_causa_raiz_label"}.issubset(normalized.columns)
    assert len(normalized) <= len(raw_frame)
