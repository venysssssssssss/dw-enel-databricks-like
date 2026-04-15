"""Profile dashboard load and aggregation latency for Sprint 14."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections.abc import Callable

import pandas as pd

from src.viz.cache import cached_aggregation, clear_memory_cache
from src.viz.erro_leitura_dashboard_data import (
    load_dashboard_frame,
    monthly_volume,
    refaturamento_by_cause,
    region_cause_matrix,
    root_cause_distribution,
    topic_distribution,
)
from src.viz.reclamacoes_ce_dashboard_data import load_reclamacoes_ce

Aggregation = Callable[[pd.DataFrame], pd.DataFrame]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--include-total", action="store_true")
    parser.add_argument("--reclamacoes-ce", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    frame = load_dashboard_frame(include_total=args.include_total)
    load_seconds = time.perf_counter() - started
    reclamacoes_load_seconds = None
    reclamacoes_rows = None
    if args.reclamacoes_ce:
        started = time.perf_counter()
        reclamacoes = load_reclamacoes_ce()
        reclamacoes_load_seconds = time.perf_counter() - started
        reclamacoes_rows = len(reclamacoes)
    aggregations: tuple[Aggregation, ...] = (
        monthly_volume,
        root_cause_distribution,
        region_cause_matrix,
        topic_distribution,
        refaturamento_by_cause,
    )

    clear_memory_cache()
    for aggregation in aggregations:
        cached_aggregation(aggregation, frame)

    durations_ms: list[float] = []
    for _ in range(args.iterations):
        for aggregation in aggregations:
            started = time.perf_counter()
            cached_aggregation(aggregation, frame)
            durations_ms.append((time.perf_counter() - started) * 1000)

    result = {
        "rows": len(frame),
        "load_seconds": round(load_seconds, 3),
        "aggregation_p95_ms": round(_p95(durations_ms), 3),
        "aggregation_max_ms": round(max(durations_ms), 3),
        "iterations": args.iterations,
        "include_total": args.include_total,
        "reclamacoes_ce_load_seconds": (
            round(reclamacoes_load_seconds, 3) if reclamacoes_load_seconds is not None else None
        ),
        "reclamacoes_ce_rows": reclamacoes_rows,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=20)[18]


if __name__ == "__main__":
    main()
