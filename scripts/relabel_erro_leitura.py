"""Relabel erro_leitura silver data with taxonomy v3 canonical causes."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.ml.models.erro_leitura_classifier import KeywordErroLeituraClassifier
from src.viz.erro_leitura_dashboard_data import DEFAULT_SILVER_PATH, TRAINING_DATA_TYPES

DEFAULT_OUTPUT_PATH = Path("data/silver/erro_leitura_normalizado_v3.csv")
DEFAULT_REPORT_PATH = Path("reports/relabel_v3.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_SILVER_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Sobrescreve o arquivo de entrada com as colunas v3 adicionadas.",
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const=str(DEFAULT_REPORT_PATH),
        default=None,
        help="Gera JSON de cobertura. Sem valor, usa reports/relabel_v3.json.",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Imprime tempo, linhas por segundo e destino final.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Amostra deterministica para smoke test sem relabelar todo o silver.",
    )
    return parser


def relabel_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if "texto_completo" not in frame.columns:
        raise ValueError("Coluna obrigatoria ausente: texto_completo")
    classifier = KeywordErroLeituraClassifier()
    out = frame.copy()
    results = [
        classifier.classify(text)
        for text in out["texto_completo"].fillna("").astype(str).tolist()
    ]
    out["causa_canonica_v3"] = [str(result["classe"]) for result in results]
    out["causa_canonica_confidence"] = [
        str(result.get("confidence", "indefinido")) for result in results
    ]
    return out


def coverage_report(frame: pd.DataFrame, *, duration_seconds: float) -> dict[str, Any]:
    total = max(len(frame), 1)
    by_region: dict[str, Any] = {}
    region_col = "_source_region" if "_source_region" in frame.columns else "regiao"
    if region_col in frame.columns:
        for region, group in frame.groupby(region_col, dropna=False):
            by_region[str(region)] = _coverage_payload(group)
    return {
        "rows": int(len(frame)),
        "duration_seconds": round(duration_seconds, 4),
        "rows_per_second": round(len(frame) / duration_seconds, 2)
        if duration_seconds > 0
        else 0.0,
        "indefinido_ratio": round(_indefinido_count(frame) / total, 6),
        "confidence": _value_counts(frame, "causa_canonica_confidence"),
        "causa_canonica_v3": _value_counts(frame, "causa_canonica_v3"),
        "by_region": by_region,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = time.perf_counter()
    frame = pd.read_csv(args.input, dtype=str, low_memory=False)
    if args.sample_size is not None and len(frame) > args.sample_size:
        frame = frame.sample(n=args.sample_size, random_state=42).sort_index()
    if "_data_type" in frame.columns:
        relabel_mask = frame["_data_type"].isin(TRAINING_DATA_TYPES)
        relabeled = frame.copy()
        relabeled["causa_canonica_v3"] = "indefinido"
        relabeled["causa_canonica_confidence"] = "indefinido"
        classified = relabel_frame(frame.loc[relabel_mask])
        for column in ("causa_canonica_v3", "causa_canonica_confidence"):
            relabeled.loc[relabel_mask, column] = classified[column]
    else:
        relabeled = relabel_frame(frame)
    duration = time.perf_counter() - started

    output_path = args.input if args.in_place else args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    relabeled.to_csv(output_path, index=False)

    if args.report is not None:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                coverage_report(relabeled, duration_seconds=duration),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if args.benchmark:
        rows_per_second = len(relabeled) / duration if duration > 0 else 0.0
        print(
            "relabel_erro_leitura:"
            f"rows={len(relabeled)}:"
            f"seconds={duration:.4f}:"
            f"rows_per_second={rows_per_second:.2f}:"
            f"output={output_path}"
        )
    return 0


def _coverage_payload(frame: pd.DataFrame) -> dict[str, Any]:
    total = max(len(frame), 1)
    return {
        "rows": int(len(frame)),
        "indefinido_ratio": round(_indefinido_count(frame) / total, 6),
        "confidence": _value_counts(frame, "causa_canonica_confidence"),
    }


def _indefinido_count(frame: pd.DataFrame) -> int:
    if "causa_canonica_v3" not in frame.columns:
        return 0
    return int(frame["causa_canonica_v3"].fillna("").astype(str).eq("indefinido").sum())


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in frame.columns:
        return {}
    return {
        str(key): int(value)
        for key, value in frame[column].fillna("indefinido").astype(str).value_counts().items()
    }


if __name__ == "__main__":
    raise SystemExit(main())
