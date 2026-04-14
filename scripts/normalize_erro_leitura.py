"""Normalize erro de leitura Bronze extracts into a local Silver CSV."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.ingestion.descricoes_enel_ingestor import read_excel_directory
from src.transformation.processors.erro_leitura_normalizer import normalize_erro_leitura_frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("DESCRICOES_ENEL"))
    parser.add_argument("--output", type=Path, default=Path("data/silver/erro_leitura_normalizado.csv"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    raw_frame, _ = read_excel_directory(args.input_dir)
    normalized = normalize_erro_leitura_frame(raw_frame)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(args.output, index=False)
    print(f"{args.output}:{len(normalized)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
