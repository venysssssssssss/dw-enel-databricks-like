"""Base abstractions for Bronze to Silver transformations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.common.contracts import IODescriptor, RejectStats, RunManifest
from src.common.logging import bind_pipeline_context, clear_pipeline_context, get_logger

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
else:  # pragma: no cover
    DataFrame = Any
    SparkSession = Any


@dataclass(frozen=True, slots=True)
class TransformationResult:
    run_id: str
    source_name: str
    bronze_rows: int
    silver_rows: int
    duration_seconds: float
    status: str
    manifest: RunManifest


class BaseSilverTransformer(ABC):
    """Template method encapsulating read, transform, deduplicate and reconcile."""

    def __init__(self, source_name: str, spark: SparkSession) -> None:
        self.source_name = source_name
        self.spark = spark
        self.run_id = str(uuid4())
        self.logger = get_logger(self.__class__.__name__)

    def execute(self) -> TransformationResult:
        started_at = datetime.now()
        bind_pipeline_context(run_id=self.run_id, source=self.source_name, layer="silver")
        try:
            df_bronze = self._read_bronze()
            bronze_count = int(df_bronze.count())
            df_transformed = self.transform(df_bronze)
            df_deduped = self._deduplicate(df_transformed)
            silver_count = int(df_deduped.count())
            self._write_silver(df_deduped)
            self._reconcile()
            finished_at = datetime.now()
            manifest = RunManifest(
                run_id=self.run_id,
                pipeline_name="silver_transformation",
                source_name=self.source_name,
                started_at=started_at,
                finished_at=finished_at,
                duration_seconds=(finished_at - started_at).total_seconds(),
                status="SUCCESS",
                inputs=(IODescriptor(self.source_name, self._bronze_table_name(), bronze_count, "iceberg"),),
                outputs=(IODescriptor(self.source_name, self._silver_table_name(), silver_count, "iceberg"),),
                rejects=RejectStats(),
                metadata={"dedup_keys": self.get_dedup_keys()},
            )
            self.logger.info("silver_transformation_completed", bronze_rows=bronze_count, silver_rows=silver_count)
            return TransformationResult(
                run_id=self.run_id,
                source_name=self.source_name,
                bronze_rows=bronze_count,
                silver_rows=silver_count,
                duration_seconds=manifest.duration_seconds,
                status="SUCCESS",
                manifest=manifest,
            )
        finally:
            clear_pipeline_context()

    def _read_bronze(self) -> DataFrame:
        table_name = self._bronze_table_name()
        if not self.spark.catalog.tableExists(table_name):
            raise ValueError(f"Tabela Bronze `{table_name}` não existe.")
        return self.spark.table(table_name)

    def _deduplicate(self, df: DataFrame) -> DataFrame:
        from src.transformation.processors.deduplicator import deduplicate

        return deduplicate(df, keys=self.get_dedup_keys(), order_col=self.get_dedup_order())

    def _write_silver(self, df: DataFrame) -> None:
        table_name = self._silver_table_name()
        writer = df.writeTo(table_name).using("iceberg")
        if self.spark.catalog.tableExists(table_name):
            writer.overwritePartitions()
        else:
            writer.create()

    def _reconcile(self) -> None:
        try:
            from src.quality.reconciliation import LayerReconciler

            LayerReconciler(self.spark).reconcile(
                self._bronze_table_name(),
                self._silver_table_name(),
                "bronze_to_silver",
            )
        except Exception as exc:  # pragma: no cover
            self.logger.warning("silver_reconciliation_failed", error=str(exc))

    def _bronze_table_name(self) -> str:
        return f"nessie.bronze.{self.source_name}"

    def _silver_table_name(self) -> str:
        return f"nessie.silver.{self.source_name}"

    def add_silver_metadata(self, df: DataFrame) -> DataFrame:
        from pyspark.sql.functions import col, current_timestamp, lit

        return (
            df.withColumn("_source_run_id", col("_run_id") if "_run_id" in df.columns else lit(None).cast("string"))
            .withColumn("_run_id", lit(self.run_id))
            .withColumn("_processed_at", current_timestamp())
            .withColumn("_valid_from", current_timestamp())
            .withColumn("_valid_to", lit(None).cast("timestamp"))
            .withColumn("_is_current", lit(True))
        )

    @abstractmethod
    def transform(self, df: DataFrame) -> DataFrame:
        """Apply domain-specific transformation logic."""

    @abstractmethod
    def get_dedup_keys(self) -> list[str]:
        """Columns that define the latest valid record."""

    @abstractmethod
    def get_dedup_order(self) -> str:
        """Ordering column used by deduplication."""
