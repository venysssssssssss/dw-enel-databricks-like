"""Warm up the unified data-plane caches used by API, BI and RAG."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_plane import DataStore  # noqa: E402
from src.data_plane.views import VIEW_REGISTRY  # noqa: E402

DEFAULT_FILTERS: tuple[dict[str, Any], ...] = (
    {},
    {"regiao": ["CE"]},
    {"regiao": ["SP"]},
    {"status": ["ABERTO"]},
)
DEFAULT_VIEWS = (
    "overview",
    "by_region",
    "top_assuntos",
    "top_causas",
    "refaturamento_summary",
    "monthly_volume",
    "mis",
    "severity_heatmap",
    "reincidence_matrix",
)


def warmup(
    *,
    store: DataStore | None = None,
    views: tuple[str, ...] = DEFAULT_VIEWS,
    filters: tuple[dict[str, Any], ...] = DEFAULT_FILTERS,
) -> dict[str, Any]:
    started = time.perf_counter()
    data_store = store or DataStore()
    version = data_store.version()
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for view_id in views:
        if view_id not in VIEW_REGISTRY:
            failures.append({"view_id": view_id, "error": "view desconhecida"})
            continue
        for filter_set in filters:
            try:
                records = data_store.aggregate_records(view_id, filter_set)
            except Exception as exc:  # pragma: no cover - CLI diagnostic path.
                failures.append({"view_id": view_id, "error": str(exc)})
                continue
            results.append(
                {
                    "view_id": view_id,
                    "filters": filter_set,
                    "rows": len(records),
                }
            )

    cards = data_store.cards()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "dataset_hash": version.hash,
        "sources": version.sources,
        "views": results,
        "cards": len(cards),
        "failures": failures,
        "elapsed_ms": round(elapsed_ms, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preaquece caches do data plane ENEL.")
    parser.add_argument(
        "--views",
        nargs="*",
        default=list(DEFAULT_VIEWS),
        help="Lista de view_ids para aquecer.",
    )
    args = parser.parse_args()

    report = warmup(views=tuple(args.views))
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
