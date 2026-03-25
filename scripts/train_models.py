"""Train all documented ML models from the local feature store."""

from __future__ import annotations

import argparse
from datetime import date

from src.ml.feature_store import FeatureStore
from src.ml.models import (
    AnomaliaModelTrainer,
    AtrasoModelTrainer,
    InadimplenciaModelTrainer,
    MetasModelTrainer,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-date", type=date.fromisoformat, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    feature_store = FeatureStore()
    trainers = [
        AtrasoModelTrainer(feature_store),
        InadimplenciaModelTrainer(feature_store),
        MetasModelTrainer(feature_store),
        AnomaliaModelTrainer(feature_store),
    ]
    for trainer in trainers:
        result = trainer.train(args.test_date)
        print(
            f"{result.model_name}:{result.version}:"
            f"train={result.train_rows}:test={result.test_rows}:metrics={result.metrics}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
