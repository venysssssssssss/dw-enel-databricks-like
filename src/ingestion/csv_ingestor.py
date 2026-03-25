"""CSV ingestion implementation for Bronze sources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.ingestion.base import BaseIngestor

if TYPE_CHECKING:
    from pyspark.sql import DataFrame
else:  # pragma: no cover
    DataFrame = Any


class CSVIngestor(BaseIngestor):
    def extract(self) -> DataFrame:
        cfg = self.config.source
        return (
            self.spark.read.option("header", cfg.has_header)
            .option("delimiter", cfg.delimiter)
            .option("encoding", cfg.encoding)
            .option("inferSchema", "false")
            .csv(str(self.resolve_source_path()))
        )
