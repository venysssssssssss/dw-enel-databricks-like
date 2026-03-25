"""Entregas de fatura Bronze ingestor."""

from __future__ import annotations

from src.ingestion.incremental_ingestor import IncrementalIngestor


class EntregasFaturaIngestor(IncrementalIngestor):
    REQUIRED_COLUMNS = {"cod_entrega", "cod_fatura", "cod_uc", "data_registro"}

    def post_extract_validation(self, df) -> None:  # type: ignore[override]
        super().post_extract_validation(df)
        missing = sorted(self.REQUIRED_COLUMNS.difference(df.columns))
        if missing:
            raise ValueError(f"Colunas faltando na fonte entregas_fatura: {missing}")
