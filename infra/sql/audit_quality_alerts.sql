CREATE TABLE IF NOT EXISTS nessie.audit.quality_alerts (
    severity STRING,
    table_name STRING,
    expectation STRING,
    details STRING,
    created_at TIMESTAMP
)
USING iceberg
PARTITIONED BY (month(created_at));
