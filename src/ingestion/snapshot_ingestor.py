"""Snapshot ingestion that replaces the target logical partition."""

from __future__ import annotations

from src.ingestion.base import BaseIngestor


class SnapshotIngestor(BaseIngestor):
    def _write_bronze(self, df) -> None:  # type: ignore[override]
        table_name = self._bronze_table_name()
        writer = df.writeTo(table_name).using("iceberg")
        if self.spark.catalog.tableExists(table_name):
            writer.overwritePartitions()
        else:
            writer.create()
