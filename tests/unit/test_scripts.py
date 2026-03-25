from __future__ import annotations

from datetime import date
from pathlib import Path

from src.common.sample_data import generate_sample_files
from scripts.bootstrap_sql import main as bootstrap_sql_main
from scripts.seed_dim_tempo import build_rows


def test_generate_sample_files(tmp_path: Path) -> None:
    files = generate_sample_files(rows=20, output_dir=tmp_path)
    assert any(file.name == "notas_operacionais.csv" for file in files)
    assert all(file.exists() for file in files)


def test_seed_dim_tempo_rows_cover_ufs() -> None:
    rows = build_rows(date(2026, 1, 1), date(2026, 1, 2))
    assert {row["uf"] for row in rows} == {"SP", "RJ", "CE", "GO"}
    assert all("flag_dia_util" in row for row in rows)


def test_bootstrap_sql_command_writes_files(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sys.argv", ["bootstrap_sql.py", "--output-dir", str(tmp_path)])
    result = bootstrap_sql_main()
    assert result == 0
    assert (tmp_path / "bronze_notas_operacionais.sql").exists()
