"""DDL helpers for Bronze and audit tables."""

from __future__ import annotations

from src.common.contracts import SourceConfig


TECHNICAL_COLUMNS = [
    ("_run_id", "STRING"),
    ("_ingested_at", "TIMESTAMP"),
    ("_source_file", "STRING"),
    ("_source_hash", "STRING"),
    ("_partition_date", "DATE"),
]


def render_bronze_table_ddl(config: SourceConfig) -> str:
    business_columns = [f"    {column.name} STRING" for column in config.columns]
    technical_columns = [f"    {name} {type_name}" for name, type_name in TECHNICAL_COLUMNS]
    columns_sql = ",\n".join([*business_columns, *technical_columns])
    return f"""CREATE TABLE IF NOT EXISTS nessie.bronze.{config.source.name} (
{columns_sql}
)
USING iceberg
PARTITIONED BY (_partition_date);"""


def render_ingestion_audit_ddl() -> str:
    return """CREATE TABLE IF NOT EXISTS nessie.audit.ingestion_log (
    run_id STRING,
    source_name STRING,
    ingestion_type STRING,
    rows_ingested BIGINT,
    partition_date DATE,
    watermark_value STRING,
    duration_seconds DOUBLE,
    status STRING,
    error_message STRING,
    dag_id STRING,
    task_id STRING,
    executed_at TIMESTAMP
)
USING iceberg
PARTITIONED BY (month(executed_at));"""
