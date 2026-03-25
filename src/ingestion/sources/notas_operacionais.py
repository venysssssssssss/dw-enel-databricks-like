"""Notas operacionais Bronze ingestor."""

from __future__ import annotations

from src.ingestion.incremental_ingestor import IncrementalIngestor


class NotasOperacionaisIngestor(IncrementalIngestor):
    REQUIRED_COLUMNS = {
        "cod_nota",
        "cod_uc",
        "data_criacao",
        "status",
        "data_alteracao",
    }

    def post_extract_validation(self, df) -> None:  # type: ignore[override]
        super().post_extract_validation(df)
        missing = sorted(self.REQUIRED_COLUMNS.difference(df.columns))
        if missing:
            raise ValueError(f"Colunas faltando na fonte notas_operacionais: {missing}")
