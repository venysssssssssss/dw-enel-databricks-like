from __future__ import annotations

from src.ingestion.config_loader import load_source_config


def test_loads_notas_config() -> None:
    config = load_source_config("notas_operacionais")
    assert config.source.name == "notas_operacionais"
    assert config.ingestion.strategy == "incremental"
    assert "cod_nota" in config.schema_columns()


def test_loads_snapshot_config() -> None:
    config = load_source_config("cadastro_bases")
    assert config.ingestion.strategy == "snapshot"
