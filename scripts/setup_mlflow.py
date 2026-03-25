"""Create the documented MLflow experiments when MLflow is available."""

from __future__ import annotations

import argparse

from src.common.config import get_settings

try:  # pragma: no cover
    import mlflow
except ImportError:  # pragma: no cover
    mlflow = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracking-uri", default=None, help="Override do tracking URI do MLflow.")
    return parser


def main() -> int:
    settings = get_settings()
    args = build_parser().parse_args()
    tracking_uri = args.tracking_uri or settings.mlflow_tracking_uri
    if mlflow is None:
        print("MLflow nao esta instalado; setup ignorado.")
        return 0

    mlflow.set_tracking_uri(tracking_uri)
    for experiment in settings.mlflow_experiments:
        try:
            experiment_id = mlflow.create_experiment(
                experiment,
                artifact_location=f"s3://{settings.minio_bucket_ml_artifacts}/{experiment}",
            )
            print(f"{experiment}: created:{experiment_id}")
        except Exception:
            existing = mlflow.get_experiment_by_name(experiment)
            if existing is None:
                raise
            print(f"{experiment}: exists:{existing.experiment_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
