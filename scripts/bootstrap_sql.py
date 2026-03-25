"""Generate SQL bootstrap files for Bronze, Silver and audit tables."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.ingestion.config_loader import get_config_directory, load_source_config
from src.ingestion.table_sql import render_bronze_table_ddl, render_ingestion_audit_ddl
from src.transformation.table_sql import (
    render_quality_alerts_ddl,
    render_reconciliation_audit_ddl,
    render_silver_notas_operacionais_ddl,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("infra/sql"), help="Diretório de saída dos arquivos SQL.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for config_file in sorted(get_config_directory().glob("*.yml")):
        config = load_source_config(config_file.stem)
        bronze_sql = render_bronze_table_ddl(config)
        (args.output_dir / f"bronze_{config.source.name}.sql").write_text(bronze_sql + "\n", encoding="utf-8")

    (args.output_dir / "audit_ingestion_log.sql").write_text(render_ingestion_audit_ddl() + "\n", encoding="utf-8")
    (args.output_dir / "audit_reconciliation_log.sql").write_text(render_reconciliation_audit_ddl() + "\n", encoding="utf-8")
    (args.output_dir / "audit_quality_alerts.sql").write_text(render_quality_alerts_ddl() + "\n", encoding="utf-8")
    (args.output_dir / "silver_notas_operacionais.sql").write_text(render_silver_notas_operacionais_ddl() + "\n", encoding="utf-8")
    for sql_file in sorted(args.output_dir.glob("*.sql")):
        print(sql_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
