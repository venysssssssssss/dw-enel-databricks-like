"""Run batch scoring for all production models."""

from __future__ import annotations

import argparse
from datetime import date

from src.ml.feature_store import FeatureStore
from src.ml.scoring import AnomaliaScorer, AtrasoScorer, InadimplenciaScorer, MetasScorer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scoring-date", type=date.fromisoformat, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    feature_store = FeatureStore()
    scorers = [
        AtrasoScorer("atraso_entrega", feature_store),
        InadimplenciaScorer("inadimplencia", feature_store),
        MetasScorer("metas", feature_store),
        AnomaliaScorer("anomalias", feature_store),
    ]
    for scorer in scorers:
        result = scorer.score(args.scoring_date)
        print(f"{result.model_name}:{result.rows_scored}:{result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
