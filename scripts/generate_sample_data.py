"""Generate synthetic sample data for all priority sources."""

from __future__ import annotations

import argparse

from src.common.sample_data import generate_sample_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1000, help="Número de linhas para datasets transacionais.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    files = generate_sample_files(rows=args.rows)
    for file_path in files:
        print(file_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
