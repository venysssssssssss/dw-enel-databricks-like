CREATE TABLE IF NOT EXISTS nessie.bronze.cadastro_distribuidoras (
    cod_distribuidora STRING,
    nome_distribuidora STRING,
    uf STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
