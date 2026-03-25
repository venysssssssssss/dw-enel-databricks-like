CREATE TABLE IF NOT EXISTS nessie.audit.reconciliation_log (
    run_id STRING,
    layer_pair STRING,
    table_name STRING,
    source_count BIGINT,
    target_count BIGINT,
    delta_count BIGINT,
    delta_pct DOUBLE,
    status STRING,
    threshold_pct DOUBLE,
    executed_at TIMESTAMP
)
USING iceberg
PARTITIONED BY (month(executed_at));
