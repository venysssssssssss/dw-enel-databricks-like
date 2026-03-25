CREATE TABLE IF NOT EXISTS nessie.bronze.pagamentos (
    cod_pagamento STRING,
    cod_fatura STRING,
    cod_uc STRING,
    valor_fatura STRING,
    valor_pago STRING,
    data_vencimento STRING,
    data_pagamento STRING,
    forma_pagamento STRING,
    data_processamento STRING,
    _run_id STRING,
    _ingested_at TIMESTAMP,
    _source_file STRING,
    _source_hash STRING,
    _partition_date DATE
)
USING iceberg
PARTITIONED BY (_partition_date);
