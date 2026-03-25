CREATE TABLE IF NOT EXISTS nessie.bronze.cadastro_uts (
    cod_ut STRING,
    cod_distribuidora STRING,
    nome_ut STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
