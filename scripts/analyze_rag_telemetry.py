"""Summarize local RAG telemetry without exposing full chat content.

Diagnoses bottlenecks (slow tail, cache miss patterns, fatura/medidor coverage)
and prints actionable recommendations.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_FATURA_MEDIDOR_TERMS = (
    "fatura",
    "medidor",
    "leitura",
    "digital",
    "analógic",
    "analogic",
    "ciclom",
    "consumo",
    "refatur",
    "valor",
)


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


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = int(p * (len(ordered) - 1))
    return float(ordered[idx])


def _latency_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p50": None, "p95": None, "p99": None, "max": None}
    return {
        "p50": round(statistics.median(values), 2),
        "p95": round(_percentile(values, 0.95) or 0.0, 2),
        "p99": round(_percentile(values, 0.99) or 0.0, 2),
        "max": round(max(values), 2),
    }


def _is_fatura_medidor(text: str) -> bool:
    text_l = text.lower()
    return any(term in text_l for term in _FATURA_MEDIDOR_TERMS)


def analyze(path: Path) -> dict[str, Any]:
    rows = _read_rows(path)
    total = len(rows)
    if not total:
        return {"turns": 0}

    cache_hits = sum(1 for r in rows if r.get("cache_hit"))
    misses = [r for r in rows if not r.get("cache_hit") and r.get("provider") != "stub"]
    miss_lat = [float(r.get("latency_total_ms") or 0.0) for r in misses]
    all_lat = [float(r.get("latency_total_ms") or 0.0) for r in rows]

    by_intent: dict[str, list[float]] = defaultdict(list)
    for r in misses:
        by_intent[str(r.get("intent_class") or "unknown")].append(
            float(r.get("latency_total_ms") or 0.0)
        )
    intent_latency = {
        k: {"n": len(v), **_latency_summary(v)} for k, v in by_intent.items()
    }

    # Cache promotion candidates: questions with >=3 misses
    miss_previews = Counter(
        (r.get("question_preview") or "").strip()[:120] for r in misses
    )
    promotion_candidates = [
        {"preview": prev, "miss_count": cnt}
        for prev, cnt in miss_previews.most_common(50)
        if cnt >= 3 and prev
    ]

    # Fatura/medidor coverage
    fm_rows = [r for r in rows if _is_fatura_medidor(r.get("question_preview") or "")]
    fm_misses = [r for r in fm_rows if not r.get("cache_hit") and r.get("provider") != "stub"]
    fm_lat = [float(r.get("latency_total_ms") or 0.0) for r in fm_misses]

    # Region split
    region_counts = Counter(r.get("region_detected") for r in rows)

    # Slowest individual turns
    slow_top = sorted(
        rows,
        key=lambda r: float(r.get("latency_total_ms") or 0.0),
        reverse=True,
    )[:10]
    slowest = [
        {
            "preview": (r.get("question_preview") or "")[:80],
            "latency_ms": round(float(r.get("latency_total_ms") or 0.0), 0),
            "intent": r.get("intent_class"),
            "region": r.get("region_detected"),
            "n_passages": r.get("n_passages"),
        }
        for r in slow_top
    ]

    return {
        "turns": total,
        "unique_hashes": len({r.get("question_hash") for r in rows}),
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / total, 4),
        "miss_count": len(misses),
        "latency_total_ms_all": _latency_summary(all_lat),
        "latency_total_ms_misses": _latency_summary(miss_lat),
        "intent_counts": Counter(r.get("intent_class") for r in rows).most_common(10),
        "region_counts": region_counts.most_common(),
        "intent_latency_misses": intent_latency,
        "fatura_medidor": {
            "total": len(fm_rows),
            "misses": len(fm_misses),
            "latency_misses": _latency_summary(fm_lat),
            "share_of_misses": round(len(fm_misses) / max(1, len(misses)), 3),
        },
        "cache_promotion_candidates": promotion_candidates,
        "slowest_turns": slowest,
    }


def _bottleneck_report(stats: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if not stats.get("turns"):
        return ["[empty] no telemetry rows."]

    cache_rate = stats["cache_hit_rate"]
    p95 = (stats["latency_total_ms_misses"] or {}).get("p95")
    fm = stats["fatura_medidor"]

    lines.append("=== BOTTLENECK REPORT ===")
    lines.append(f"turns={stats['turns']}  cache_hit_rate={cache_rate:.1%}")
    if p95 is not None:
        lines.append(f"miss latency p95={p95:.0f}ms p99={stats['latency_total_ms_misses']['p99']:.0f}ms")

    by_intent = stats.get("intent_latency_misses", {})
    slow_intents = sorted(
        by_intent.items(),
        key=lambda kv: kv[1].get("p95") or 0,
        reverse=True,
    )[:3]
    if slow_intents:
        lines.append("slowest intents (miss p95):")
        for name, m in slow_intents:
            lines.append(f"  - {name}: n={m['n']} p95={(m.get('p95') or 0):.0f}ms")

    lines.append(
        f"fatura/medidor: {fm['misses']} misses ({fm['share_of_misses']:.0%} of all misses), "
        f"p95={(fm['latency_misses'].get('p95') or 0):.0f}ms"
    )

    lines.append("")
    lines.append("=== RECOMMENDATIONS ===")
    if cache_rate < 0.30:
        lines.append(
            f"- low cache hit rate ({cache_rate:.0%}). Promote {len(stats['cache_promotion_candidates'])} "
            f"repeated questions: scripts/promote_positive_cache.py"
        )
    if (p95 or 0) > 60_000:
        lines.append(
            "- miss p95 > 60s. Reduce LLM completion budget or pre-warm answers via teacher loop."
        )
    if fm["share_of_misses"] >= 0.20:
        lines.append(
            "- fatura/medidor dominates misses. Ingest DESCRICOES_ENEL/erro_leitura_clusterizado.csv "
            "and add cluster card boosts."
        )
    glossario = by_intent.get("glossario") or {}
    if (glossario.get("p95") or 0) > 60_000:
        lines.append(
            "- glossario p95 > 60s. Glossário deveria ser cache 100% — popular known_questions/positive_cache."
        )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Analisa telemetria local do RAG.")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("data/rag/telemetry.jsonl"),
        help="Caminho do JSONL de telemetria.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Imprime relatório de gargalos + recomendações em texto plano.",
    )
    args = parser.parse_args()
    stats = analyze(args.path)
    if args.report:
        print("\n".join(_bottleneck_report(stats)))
        return 0
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
