"""Incremental ingestion with watermark filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.ingestion.csv_ingestor import CSVIngestor

if TYPE_CHECKING:
    from pyspark.sql import DataFrame
else:  # pragma: no cover
    DataFrame = Any


class IncrementalIngestor(CSVIngestor):
    def extract(self) -> DataFrame:
        from pyspark.sql.functions import col, lit, to_date, to_timestamp

        df_full = super().extract()
        watermark_col = self.config.ingestion.watermark_column
        last_watermark = self._get_last_watermark()
        if watermark_col and last_watermark is not None:
            format_hint = next(
                (column.format for column in self.config.columns if column.name == watermark_col),
                None,
            )
            if format_hint:
                if "HH" in format_hint:
                    return df_full.filter(
                        to_timestamp(col(watermark_col), format_hint)
                        > to_timestamp(lit(last_watermark), format_hint)
                    )
                return df_full.filter(
                    to_date(col(watermark_col), format_hint) > to_date(lit(last_watermark), format_hint)
                )
        return df_full

    def _get_last_watermark(self) -> str | None:
        audit_table = f"{self.settings.audit_namespace}.ingestion_log"
        if not self.spark.catalog.tableExists(audit_table):
            return None
        watermark_col = self.config.ingestion.watermark_column
        if watermark_col is None:
            return None
        rows = (
            self.spark.table(audit_table)
            .filter(f"source_name = '{self.config.source.name}' AND status = 'SUCCESS'")
            .orderBy("executed_at", ascending=False)
            .limit(1)
            .collect()
        )
        if not rows:
            return None
        value = rows[0]["watermark_value"]
        return str(value) if value else None
