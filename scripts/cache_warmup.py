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
from src.rag.answer_cache import render_cached_answer  # noqa: E402
from src.rag.known_questions import (  # noqa: E402
    KNOWN_QUESTION_SEEDS,
    SEED_VERSION,
    known_variant_count,
)
from src.rag.retriever import Passage  # noqa: E402

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


def warmup_rag_known_answers(
    *,
    store: DataStore | None = None,
    output_path: Path = Path("data/rag/known_answers.json"),
) -> dict[str, Any]:
    started = time.perf_counter()
    data_store = store or DataStore()
    version = data_store.version()
    cards = data_store.cards()
    by_anchor = {
        str(card.anchor): Passage(
            chunk_id=str(card.chunk_id),
            text=str(card.text),
            source_path=str(card.source_path),
            section=str(card.section),
            doc_type=str(card.doc_type),
            sprint_id=str(card.sprint_id),
            anchor=str(card.anchor),
            score=0.99,
            dataset_version=str(card.dataset_version),
            region=str(card.region),
            scope=str(card.scope),
            data_source=str(card.data_source),
        )
        for card in cards
    }
    answers: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    for seed in KNOWN_QUESTION_SEEDS:
        passages = [by_anchor[anchor] for anchor in seed.anchors if anchor in by_anchor]
        if seed.anchors and not passages:
            misses.append({"seed_id": seed.seed_id, "anchors": list(seed.anchors)})
            continue
        text = render_cached_answer(seed, passages) if passages else ""
        answers.append(
            {
                "seed_id": seed.seed_id,
                "intent": seed.intent,
                "region": seed.region,
                "answer_mode": seed.answer_mode,
                "variants": list(seed.variants),
                "anchors": list(seed.anchors),
                "text": text,
            }
        )
    payload = {
        "dataset_hash": version.hash,
        "seed_version": SEED_VERSION,
        "known_variants": known_variant_count(),
        "answers_count": len(answers),
        "misses": misses,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "answers": answers,
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "dataset_hash": version.hash,
        "seed_version": SEED_VERSION,
        "known_variants": known_variant_count(),
        "answers_count": len(answers),
        "misses": misses,
        "output_path": str(output_path),
        "elapsed_ms": payload["elapsed_ms"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preaquece caches do data plane ENEL.")
    parser.add_argument(
        "--views",
        nargs="*",
        default=list(DEFAULT_VIEWS),
        help="Lista de view_ids para aquecer.",
    )
    parser.add_argument(
        "--rag-known-answers",
        action="store_true",
        help="Materializa cache local de respostas conhecidas do RAG.",
    )
    args = parser.parse_args()

    report = warmup(views=tuple(args.views))
    if args.rag_known_answers:
        report["rag_known_answers"] = warmup_rag_known_answers()
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
