from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.ingestion.descricoes_enel_ingestor import (
    classify_sheet,
    derive_source_region,
    read_excel_directory,
)


def _write_workbook(path: Path, sheet_name: str) -> None:
    frame = pd.DataFrame(
        [
            {
                "GRUPO": "N1",
                "ORDEM": "123",
                "ASSUNTO": "Erro de leitura",
                "INSTALACAO": "456",
                "DT. INGRESSO": "2026-01-01",
                "OBSERVAÇÃO ORDEM": "Cliente informa leitura estimada",
                "Status": "Encerrada",
                "DEVOLUTIVA": "Refaturamento realizado",
                "Causa Raiz": "Leitura estimada",
            }
        ]
    )
    with pd.ExcelWriter(path) as writer:
        frame.to_excel(writer, sheet_name=sheet_name, index=False)


def test_region_and_sheet_classification() -> None:
    assert derive_source_region(Path("TRATADO Trimestre_Ordens (2).xlsx")) == "SP"
    assert derive_source_region(Path("reclamacoes_total_2026.xlsx")) == "CE"
    assert classify_sheet("ERRO DE LEITURA", Path("reclamacoes_total_2026.xlsx")) == "erro_leitura"
    assert classify_sheet("Base N1", Path("TRATADO Trimestre_Ordens (2).xlsx")) == "base_n1_sp"


def test_read_excel_directory_preserves_sheet_metadata(tmp_path: Path) -> None:
    _write_workbook(tmp_path / "reclamacoes_total_2026.xlsx", "erro de leitura")
    _write_workbook(tmp_path / "TRATADO Trimestre_Ordens (2).xlsx", "Base N1")

    frame, summaries = read_excel_directory(tmp_path)

    assert len(frame) == 2
    assert {summary.source_region for summary in summaries} == {"CE", "SP"}
    assert {"_sheet_name", "_data_type", "_source_region", "_source_hash"}.issubset(frame.columns)
    assert set(frame["_data_type"]) == {"erro_leitura", "base_n1_sp"}
