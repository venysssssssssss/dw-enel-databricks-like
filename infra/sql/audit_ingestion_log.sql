CREATE TABLE IF NOT EXISTS nessie.audit.ingestion_log (
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
PARTITIONED BY (month(executed_at));
