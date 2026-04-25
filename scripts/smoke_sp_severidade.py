"""Smoke probe for the sp_severidade_* aggregation family.

Usage:
    .venv/bin/python -m scripts.smoke_sp_severidade --view sp_severidade_alta_overview
    .venv/bin/python -m scripts.smoke_sp_severidade --all

Returns non-zero exit when any selected view fails to aggregate.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from src.data_plane import DataStore
from src.data_plane.views import VIEW_REGISTRY


SP_SEVERIDADE_VIEWS = sorted(v for v in VIEW_REGISTRY if v.startswith("sp_severidade_"))


def _probe(view_id: str, store: DataStore) -> dict:
    started = time.perf_counter()
    try:
        records = store.aggregate_records(view_id)
    except Exception as exc:  # pragma: no cover
        return {
            "view_id": view_id,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "rows": 0,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
    return {
        "view_id": view_id,
        "ok": True,
        "rows": len(records),
        "first": records[0] if records else None,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke probe SP severidade views")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--view", help="single view_id to probe")
    group.add_argument("--all", action="store_true", help="probe all sp_severidade_* views")
    args = parser.parse_args(argv)

    store = DataStore()
    targets = [args.view] if args.view else SP_SEVERIDADE_VIEWS
    if not targets:
        print("No sp_severidade_* views registered", file=sys.stderr)
        return 1

    results = [_probe(view_id, store) for view_id in targets]
    json.dump(results, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    return 0 if all(r["ok"] for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
