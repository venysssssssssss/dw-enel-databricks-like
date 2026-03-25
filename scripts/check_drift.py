"""Generate drift reports between two feature snapshots."""

from __future__ import annotations

import argparse
from datetime import date

from src.ml.feature_store import FeatureStore
from src.ml.monitoring import DriftDetector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--reference-date", type=date.fromisoformat, required=True)
    parser.add_argument("--current-date", type=date.fromisoformat, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    detector = DriftDetector(args.model_name, FeatureStore())
    output_path = detector.save_report(args.reference_date, args.current_date)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
