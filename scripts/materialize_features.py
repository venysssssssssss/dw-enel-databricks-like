"""Materialize local feature-store snapshots from the sample datasets."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from src.common.config import get_settings
from src.ml.feature_store import FeatureStore
from src.ml.features import (
    AnomaliaFeatureBuilder,
    AtrasoFeatureBuilder,
    InadimplenciaFeatureBuilder,
    MetasFeatureBuilder,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation-date", type=date.fromisoformat, required=True)
    parser.add_argument("--sample-dir", type=Path, default=None)
    return parser


def _load_dataset(sample_dir: Path, name: str) -> pd.DataFrame:
    dataset_path = sample_dir / f"{name}.csv"
    if not dataset_path.exists():
        return pd.DataFrame()
    return pd.read_csv(dataset_path, sep=";")


def main() -> int:
    settings = get_settings()
    args = build_parser().parse_args()
    sample_dir = args.sample_dir or settings.sample_data_path
    feature_store = FeatureStore()

    notas = _load_dataset(sample_dir, "notas_operacionais")
    pagamentos = _load_dataset(sample_dir, "pagamentos")
    ucs = _load_dataset(sample_dir, "cadastro_ucs")
    metas = _load_dataset(sample_dir, "metas_operacionais")

    feature_store.save(
        "atraso_entrega",
        args.observation_date,
        AtrasoFeatureBuilder(args.observation_date).build(notas),
        entity_key="cod_nota",
        target_columns=["target_flag_atraso", "target_dias_atraso"],
        source_files=["notas_operacionais.csv"],
    )
    feature_store.save(
        "inadimplencia",
        args.observation_date,
        InadimplenciaFeatureBuilder(args.observation_date).build(pagamentos, ucs),
        entity_key="cod_fatura",
        target_columns=["flag_inadimplente"],
        source_files=["pagamentos.csv", "cadastro_ucs.csv"],
    )
    feature_store.save(
        "metas",
        args.observation_date,
        MetasFeatureBuilder(args.observation_date).build(metas),
        entity_key="cod_base",
        target_columns=["target_pct_atingimento", "target_flag_risco"],
        source_files=["metas_operacionais.csv"],
    )
    feature_store.save(
        "anomalias",
        args.observation_date,
        AnomaliaFeatureBuilder(args.observation_date).build(notas, pagamentos),
        entity_key="entidade_id",
        source_files=["notas_operacionais.csv", "pagamentos.csv"],
    )
    for feature_set in ("atraso_entrega", "inadimplencia", "metas", "anomalias"):
        print(f"{feature_set}:{args.observation_date.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
