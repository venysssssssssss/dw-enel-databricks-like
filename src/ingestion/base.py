"""Base abstractions for Bronze ingestion pipelines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from src.common.config import get_settings
from src.common.contracts import IODescriptor, RejectStats, RunManifest, SourceConfig
from src.common.logging import bind_pipeline_context, clear_pipeline_context, get_logger

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
else:  # pragma: no cover
    DataFrame = Any
    SparkSession = Any


@dataclass(frozen=True, slots=True)
class IngestionResult:
    run_id: str
    source_name: str
    rows_ingested: int
    partition_date: str
    duration_seconds: float
    status: str
    manifest: RunManifest
    error_message: str | None = None


class BaseIngestor(ABC):
    """Template method for Bronze ingestion pipelines."""

    def __init__(self, source_config: SourceConfig, spark: SparkSession) -> None:
        self.config = source_config
        self.spark = spark
        self.run_id = str(uuid4())
        self.logger = get_logger(self.__class__.__name__)
        self.settings = get_settings()

    def execute(self) -> IngestionResult:
        start = datetime.now()
        bind_pipeline_context(run_id=self.run_id, source=self.config.source.name)
        try:
            df = self.extract()
            self.post_extract_validation(df)
            df_enriched = self._add_technical_metadata(df)
            rows_ingested = int(df_enriched.count())
            watermark_value = self._resolve_watermark_value(df_enriched)
            self._write_bronze(df_enriched)
            finished_at = datetime.now()
            duration_seconds = (finished_at - start).total_seconds()
            manifest = self._build_manifest(
                rows_ingested=rows_ingested,
                started_at=start,
                finished_at=finished_at,
                status="SUCCESS",
            )
            self._audit(
                rows_ingested=rows_ingested,
                status="SUCCESS",
                error_message=None,
                duration_seconds=duration_seconds,
                watermark_value=watermark_value,
            )
            self.logger.info("ingestion_completed", rows_ingested=rows_ingested)
            return IngestionResult(
                run_id=self.run_id,
                source_name=self.config.source.name,
                rows_ingested=rows_ingested,
                partition_date=str(date.today()),
                duration_seconds=duration_seconds,
                status="SUCCESS",
                manifest=manifest,
            )
        except Exception as exc:
            finished_at = datetime.now()
            self._audit(
                rows_ingested=0,
                status="FAILURE",
                error_message=str(exc),
                duration_seconds=(finished_at - start).total_seconds(),
                watermark_value=None,
            )
            self.logger.exception("ingestion_failed", error=str(exc))
            raise
        finally:
            clear_pipeline_context()

    @abstractmethod
    def extract(self) -> DataFrame:
        """Load raw records from the configured source."""

    def post_extract_validation(self, df: DataFrame) -> None:
        required = set(self.config.required_columns())
        missing = sorted(required.difference(df.columns))
        if missing:
            raise ValueError(
                f"Colunas obrigatórias ausentes na fonte `{self.config.source.name}`: {missing}."
            )

    def _add_technical_metadata(self, df: DataFrame) -> DataFrame:
        from pyspark.sql.functions import col, concat_ws, current_date, current_timestamp, lit, sha2

        business_columns = [column.name for column in self.config.columns if column.name in df.columns]
        return (
            df.withColumn("_run_id", lit(self.run_id))
            .withColumn("_ingested_at", current_timestamp())
            .withColumn("_source_file", lit(self.config.source.path or self.config.source.name))
            .withColumn("_source_hash", sha2(concat_ws("||", *[col(name) for name in business_columns]), 256))
            .withColumn("_partition_date", current_date())
        )

    def _bronze_table_name(self) -> str:
        return f"nessie.bronze.{self.config.source.name}"

    def _write_bronze(self, df: DataFrame) -> None:
        table_name = self._bronze_table_name()
        writer = df.writeTo(table_name).using("iceberg")
        if self.spark.catalog.tableExists(table_name):
            writer.append()
        else:
            writer.create()

    def _audit(
        self,
        *,
        rows_ingested: int,
        status: str,
        error_message: str | None,
        duration_seconds: float,
        watermark_value: str | None,
    ) -> None:
        try:
            audit_table = f"{self.settings.audit_namespace}.ingestion_log"
            record = {
                "run_id": self.run_id,
                "source_name": self.config.source.name,
                "ingestion_type": self.config.ingestion.strategy,
                "rows_ingested": rows_ingested,
                "partition_date": str(date.today()),
                "watermark_value": watermark_value or "",
                "duration_seconds": duration_seconds,
                "status": status,
                "error_message": error_message,
                "dag_id": "",
                "task_id": "",
                "executed_at": datetime.now(),
            }
            audit_df = self.spark.createDataFrame([record])
            writer = audit_df.writeTo(audit_table).using("iceberg")
            if self.spark.catalog.tableExists(audit_table):
                writer.append()
            else:
                writer.create()
        except Exception as exc:  # pragma: no cover
            self.logger.warning("audit_write_failed", error=str(exc))

    def _resolve_watermark_value(self, df: DataFrame) -> str | None:
        from pyspark.sql.functions import col, max as spark_max, to_date, to_timestamp

        watermark_column = self.config.ingestion.watermark_column
        if watermark_column is None or watermark_column not in df.columns:
            return None
        format_hint = next(
            (column_config.format for column_config in self.config.columns if column_config.name == watermark_column),
            None,
        )
        if format_hint:
            if "HH" in format_hint:
                row = (
                    df.select(spark_max(to_timestamp(col(watermark_column), format_hint)).alias("watermark_value"))
                    .collect()[0]
                )
            else:
                row = df.select(spark_max(to_date(col(watermark_column), format_hint)).alias("watermark_value")).collect()[0]
        else:
            row = df.selectExpr(f"max({watermark_column}) as watermark_value").collect()[0]
        value = row["watermark_value"]
        return None if value is None else str(value)

    def _build_manifest(
        self,
        *,
        rows_ingested: int,
        started_at: datetime,
        finished_at: datetime,
        status: str,
        error_message: str | None = None,
    ) -> RunManifest:
        input_location = self.config.source.path or f"{self.settings.raw_data_path}/{self.config.source.name}.csv"
        return RunManifest(
            run_id=self.run_id,
            pipeline_name="bronze_ingestion",
            source_name=self.config.source.name,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(finished_at - started_at).total_seconds(),
            status=status,
            inputs=(IODescriptor(name=self.config.source.name, location=input_location, format=self.config.source.type),),
            outputs=(
                IODescriptor(
                    name=self.config.source.name,
                    location=self._bronze_table_name(),
                    rows=rows_ingested,
                    format="iceberg",
                ),
            ),
            rejects=RejectStats(count=0, reasons=((error_message,) if error_message else tuple())),
            metadata={"strategy": self.config.ingestion.strategy},
        )

    def resolve_source_path(self) -> Path:
        source_path = self.config.source.path
        if source_path is None:
            raise ValueError(f"A fonte `{self.config.source.name}` não possui `path` configurado.")
        path = Path(source_path)
        if path.is_absolute():
            return path
        return self.settings.project_root_path / path
