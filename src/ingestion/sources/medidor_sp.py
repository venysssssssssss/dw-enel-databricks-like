"""Medidor SP Bronze ingestor."""

from __future__ import annotations

from src.ingestion.snapshot_ingestor import SnapshotIngestor


class MedidorSpIngestor(SnapshotIngestor):
    REQUIRED_COLUMNS = {"instalacao"}

    def post_extract_validation(self, df) -> None:  # type: ignore[override]
        super().post_extract_validation(df)
        missing = sorted(self.REQUIRED_COLUMNS.difference(df.columns))
        if missing:
            raise ValueError(f"Colunas faltando na fonte medidor_sp: {missing}")
