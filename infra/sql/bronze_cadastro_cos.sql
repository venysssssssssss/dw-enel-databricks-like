CREATE TABLE IF NOT EXISTS nessie.bronze.cadastro_cos (
    cod_co STRING,
    cod_ut STRING,
    nome_co STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
