CREATE TABLE IF NOT EXISTS nessie.bronze.cadastro_instalacoes (
    cod_instalacao STRING,
    cod_uc STRING,
    endereco STRING,
    tipo_instalacao STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
