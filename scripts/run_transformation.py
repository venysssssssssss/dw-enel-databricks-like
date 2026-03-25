"""Run a Silver transformation from the command line."""

from __future__ import annotations

import argparse

from src.common.logging import setup_logging
from src.common.spark_session import create_spark_session
from src.transformation.silver import TRANSFORMER_REGISTRY


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_name", choices=sorted(TRANSFORMER_REGISTRY.keys()))
    parser.add_argument("--memory", default="2g")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    setup_logging()
    spark = create_spark_session(app_name=f"silver-{args.source_name}", memory=args.memory)
    transformer = TRANSFORMER_REGISTRY[args.source_name](spark)
    result = transformer.execute()
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
