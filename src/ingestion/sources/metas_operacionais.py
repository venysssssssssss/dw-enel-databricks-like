"""Metas operacionais Bronze ingestor."""

from __future__ import annotations

from src.ingestion.snapshot_ingestor import SnapshotIngestor


class MetasOperacionaisIngestor(SnapshotIngestor):
    def _write_bronze(self, df) -> None:  # type: ignore[override]
        from pyspark.sql.functions import col, to_date

        table_name = self._bronze_table_name()
        writer = (
            df.withColumn("_partition_date", to_date(col("mes_referencia"), "yyyy-MM"))
            .writeTo(table_name)
            .using("iceberg")
        )
        if self.spark.catalog.tableExists(table_name):
            writer.overwritePartitions()
        else:
            writer.create()
