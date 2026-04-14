from __future__ import annotations

import pandas as pd

from src.transformation.processors.erro_leitura_normalizer import (
    clean_text,
    extract_entities,
    normalize_erro_leitura_frame,
)


def test_clean_text_removes_html_accents_and_whitespace() -> None:
    assert clean_text("  Leitura <br> ESTIMADA<br/> em São Paulo  ") == "leitura estimada em sao paulo"


def test_extract_entities_from_text() -> None:
    entities = extract_entities("protocolo 123456 cep 12345-678 uc 987654 telefone 1199999-8888 em 01/02/2026")
    assert entities.protocolos == ("123456",)
    assert entities.ceps == ("12345-678",)
    assert entities.instalacoes_mencionadas == ("987654",)
    assert entities.datas == ("01/02/2026",)


def test_normalize_erro_leitura_frame_deduplicates_and_flags_labels() -> None:
    frame = pd.DataFrame(
        [
            {
                "ordem": "001",
                "instalacao": 123.0,
                "dt_ingresso": "2026-01-01",
                "observacao_ordem": "Cliente <b>sem leitura</b>",
                "devolutiva": "Refaturamento realizado",
                "causa_raiz": "Leitura Estimada",
                "_source_region": "CE",
                "_sheet_name": "erro de leitura",
                "_data_type": "erro_leitura",
            },
            {
                "ordem": "001",
                "instalacao": 123.0,
                "dt_ingresso": "2026-01-02",
                "observacao_ordem": "Cliente sem leitura",
                "devolutiva": "Nova analise",
                "causa_raiz": None,
                "_source_region": "CE",
                "_sheet_name": "erro de leitura",
                "_data_type": "erro_leitura",
            },
        ]
    )

    normalized = normalize_erro_leitura_frame(frame)

    assert len(normalized) == 1
    assert normalized.loc[0, "ordem"] == "001"
    assert normalized.loc[0, "instalacao"] == "123"
    assert "observacao_ordem_raw" in normalized.columns
    assert "texto_completo" in normalized.columns
