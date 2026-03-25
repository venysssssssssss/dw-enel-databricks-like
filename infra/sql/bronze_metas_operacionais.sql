CREATE TABLE IF NOT EXISTS nessie.bronze.metas_operacionais (
    cod_distribuidora STRING,
    cod_ut STRING,
    cod_co STRING,
    cod_base STRING,
    indicador STRING,
    mes_referencia STRING,
    valor_meta STRING,
    valor_realizado STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
