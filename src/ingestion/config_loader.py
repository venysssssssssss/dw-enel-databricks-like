"""Helpers to load typed ingestion contracts from YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.common.config import get_settings
from src.common.contracts import SourceConfig


def get_config_directory() -> Path:
    return get_settings().project_root_path / "src/ingestion/config"


def load_source_config(source_name: str) -> SourceConfig:
    config_path = get_config_directory() / f"{source_name}.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuração da fonte `{source_name}` não encontrada em {config_path}.")
    raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return SourceConfig.model_validate(raw_config)
