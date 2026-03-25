from __future__ import annotations

from src.ingestion.config_loader import load_source_config
from src.ingestion.table_sql import render_bronze_table_ddl, render_ingestion_audit_ddl
from src.transformation.table_sql import render_quality_alerts_ddl, render_reconciliation_audit_ddl


def test_render_bronze_table_ddl_contains_technical_columns() -> None:
    sql = render_bronze_table_ddl(load_source_config("notas_operacionais"))
    assert "CREATE TABLE IF NOT EXISTS nessie.bronze.notas_operacionais" in sql
    assert "_source_hash STRING" in sql
    assert "PARTITIONED BY (_partition_date)" in sql


def test_render_audit_ddls() -> None:
    assert "ingestion_log" in render_ingestion_audit_ddl()
    assert "reconciliation_log" in render_reconciliation_audit_ddl()
    assert "quality_alerts" in render_quality_alerts_ddl()
