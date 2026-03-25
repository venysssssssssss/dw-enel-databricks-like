"""DDL helpers for Silver and quality audit tables."""

from __future__ import annotations


def render_reconciliation_audit_ddl() -> str:
    return """CREATE TABLE IF NOT EXISTS nessie.audit.reconciliation_log (
    run_id STRING,
    layer_pair STRING,
    table_name STRING,
    source_count BIGINT,
    target_count BIGINT,
    delta_count BIGINT,
    delta_pct DOUBLE,
    status STRING,
    threshold_pct DOUBLE,
    executed_at TIMESTAMP
)
USING iceberg
PARTITIONED BY (month(executed_at));"""


def render_quality_alerts_ddl() -> str:
    return """CREATE TABLE IF NOT EXISTS nessie.audit.quality_alerts (
    severity STRING,
    table_name STRING,
    expectation STRING,
    details STRING,
    created_at TIMESTAMP
)
USING iceberg
PARTITIONED BY (month(created_at));"""


def render_silver_notas_operacionais_ddl() -> str:
    return """CREATE TABLE IF NOT EXISTS nessie.silver.notas_operacionais (
    cod_nota BIGINT,
    cod_uc BIGINT,
    cod_instalacao BIGINT,
    cod_distribuidora INT,
    cod_ut INT,
    cod_co INT,
    cod_base INT,
    cod_lote INT,
    tipo_servico STRING,
    flag_impacto_faturamento BOOLEAN,
    area_classificada_risco BOOLEAN,
    historico_incidentes_12m INT,
    tipo_instalacao STRING,
    horario_agendado STRING,
    flag_risco_manual BOOLEAN,
    data_criacao DATE,
    data_prevista DATE,
    data_execucao DATE,
    data_alteracao TIMESTAMP,
    status STRING,
    cod_colaborador INT,
    latitude DOUBLE,
    longitude DOUBLE,
    classificacao_acf_asf STRING,
    dias_atraso INT,
    status_atraso STRING,
    flag_risco BOOLEAN,
    _run_id STRING,
    _processed_at TIMESTAMP,
    _source_run_id STRING,
    _valid_from TIMESTAMP,
    _valid_to TIMESTAMP,
    _is_current BOOLEAN
)
USING iceberg
PARTITIONED BY (months(data_criacao));"""
