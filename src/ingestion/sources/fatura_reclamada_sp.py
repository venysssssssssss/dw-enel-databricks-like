"""Fatura reclamada SP Bronze ingestor (Excel snapshot)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from src.ingestion.base import BaseIngestor

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
else:  # pragma: no cover
    DataFrame = Any
    SparkSession = Any


_COLUMN_MAP = {
    "ID_RECLAMACAO": "id_reclamacao",
    "DOC_IMPRESSAO": "doc_impressao",
    "VALOR_FAT RECLMADA": "valor_fat_reclamada",
    "FAT_RECLAMADA": "fat_reclamada",
    "DATA_EMISSSAO_FAT": "data_emissao_fat",
    "DATA_VENCIMENTO": "data_vencimento",
    "DATA RECLAMACAO": "data_reclamacao",
}


class FaturaReclamadaSpIngestor(BaseIngestor):
    REQUIRED_COLUMNS = {"id_reclamacao"}

    def extract(self) -> DataFrame:
        path = self.resolve_source_path()
        frame = pd.read_excel(path, dtype=str).rename(columns=_COLUMN_MAP)
        for column in _COLUMN_MAP.values():
            if column not in frame.columns:
                frame[column] = None
        frame = frame[list(_COLUMN_MAP.values())]
        return self.spark.createDataFrame(frame.astype(object).where(pd.notna(frame), None))

    def post_extract_validation(self, df) -> None:  # type: ignore[override]
        super().post_extract_validation(df)
        missing = sorted(self.REQUIRED_COLUMNS.difference(df.columns))
        if missing:
            raise ValueError(f"Colunas faltando na fonte fatura_reclamada_sp: {missing}")
