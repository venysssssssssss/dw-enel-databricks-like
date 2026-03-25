CREATE TABLE IF NOT EXISTS nessie.bronze.entregas_fatura (
    cod_entrega STRING,
    cod_fatura STRING,
    cod_uc STRING,
    cod_distribuidora STRING,
    data_emissao STRING,
    data_vencimento STRING,
    data_entrega STRING,
    lat_entrega STRING,
    lon_entrega STRING,
    lat_uc STRING,
    lon_uc STRING,
    flag_entregue STRING,
    data_registro STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
