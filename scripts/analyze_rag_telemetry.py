"""Summarize local RAG telemetry without exposing full chat content."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.answer_cache import find_known_question  # noqa: E402
from src.rag.known_questions import known_variant_count  # noqa: E402


def analyze(path: Path) -> dict[str, Any]:
    rows = _read_rows(path)
    total = len(rows)
    cache_hits = sum(1 for row in rows if row.get("cache_hit"))
    latencies = sorted(float(row.get("latency_total_ms") or 0.0) for row in rows)
    previews = [str(row.get("question_preview") or "").strip() for row in rows]
    covered = 0
    for row in rows:
        preview = str(row.get("question_preview") or "")
        if find_known_question(
            preview,
            intent=str(row.get("intent_class") or "glossario"),
            region=row.get("region_detected"),
        ):
            covered += 1
    return {
        "turns": total,
        "unique_hashes": len({row.get("question_hash") for row in rows}),
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / total, 4) if total else 0.0,
        "known_seed_variants": known_variant_count(),
        "estimated_known_coverage": round(covered / total, 4) if total else 0.0,
        "latency_total_ms": _latency_summary(latencies),
        "intent_counts": Counter(row.get("intent_class") for row in rows).most_common(20),
        "region_counts": Counter(row.get("region_detected") for row in rows).most_common(20),
        "top_question_previews": Counter(previews).most_common(50),
    }


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _latency_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p50": None, "p95": None, "max": None}
    p95_idx = int(0.95 * (len(values) - 1))
    return {
        "p50": round(statistics.median(values), 2),
        "p95": round(values[p95_idx], 2),
        "max": round(max(values), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analisa telemetria local do RAG.")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("data/rag/telemetry.jsonl"),
        help="Caminho do JSONL de telemetria.",
    )
    args = parser.parse_args()
    print(json.dumps(analyze(args.path), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
