"""Run a Bronze ingestion source from the command line."""

from __future__ import annotations

import argparse

from src.common.logging import setup_logging
from src.common.spark_session import create_spark_session
from src.ingestion.config_loader import load_source_config
from src.ingestion.sources import INGESTION_SOURCE_REGISTRY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_name", choices=sorted(INGESTION_SOURCE_REGISTRY.keys()))
    parser.add_argument("--memory", default="2g")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    setup_logging()
    config = load_source_config(args.source_name)
    spark = create_spark_session(app_name=f"ingest-{args.source_name}", memory=args.memory)
    ingestor = INGESTION_SOURCE_REGISTRY[args.source_name](config, spark)
    result = ingestor.execute()
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
