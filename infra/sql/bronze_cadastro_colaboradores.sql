CREATE TABLE IF NOT EXISTS nessie.bronze.cadastro_colaboradores (
    cod_colaborador STRING,
    nome_colaborador STRING,
    equipe STRING,
    funcao STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
