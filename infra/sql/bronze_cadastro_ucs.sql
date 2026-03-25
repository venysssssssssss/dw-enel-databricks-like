CREATE TABLE IF NOT EXISTS nessie.bronze.cadastro_ucs (
    cod_uc STRING,
    cod_base STRING,
    classe_consumo STRING,
    tipo_ligacao STRING,
    status_uc STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
