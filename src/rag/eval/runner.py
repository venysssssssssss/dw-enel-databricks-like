"""Runner de avaliação para golden dataset RAG CE/SP."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.rag.eval.metrics import (
    answer_exactness,
    citation_accuracy,
    fallback_guardrail_success,
    mrr,
    ndcg_at_k,
    recall_at_k,
    refusal_rate,
    regional_compliance,
)
from src.rag.orchestrator import RagOrchestrator

if TYPE_CHECKING:
    from pathlib import Path

    from src.rag.config import RagConfig


@dataclass(frozen=True, slots=True)
class GoldenCase:
    id: str
    question: str
    expected_intent: str
    expected_region: str | None
    expected_sources: list[str]
    expected_keywords: list[str]
    forbidden_keywords: list[str]
    answer_must_cite_numbers: bool
    answer_must_refuse: bool


def load_golden(path: Path) -> list[GoldenCase]:
    if not path.exists():
        raise FileNotFoundError(f"Golden dataset não encontrado: {path}")
    cases: list[GoldenCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        cases.append(
            GoldenCase(
                id=str(raw["id"]),
                question=str(raw["question"]),
                expected_intent=str(raw.get("expected_intent", "")),
                expected_region=raw.get("expected_region"),
                expected_sources=list(raw.get("expected_sources", [])),
                expected_keywords=list(raw.get("expected_keywords", [])),
                forbidden_keywords=list(raw.get("forbidden_keywords", [])),
                answer_must_cite_numbers=bool(raw.get("answer_must_cite_numbers", False)),
                answer_must_refuse=bool(raw.get("answer_must_refuse", False)),
            )
        )
    return cases


def run_eval(
    config: RagConfig,
    *,
    golden_path: Path,
    dataset_version: str | None = None,
) -> dict[str, Any]:
    orch = RagOrchestrator(config)
    cases = load_golden(golden_path)

    recall5_values: list[float] = []
    mrr10_values: list[float] = []
    ndcg10_values: list[float] = []
    citation_values: list[float] = []
    exactness_values: list[float] = []
    latencies: list[float] = []
    refusal_answers: list[str] = []
    refusal_expecteds: list[bool] = []
    passage_regions: list[list[str]] = []
    rows: list[dict[str, Any]] = []

    for case in cases:
        response = orch.answer(
            case.question,
            dataset_version=dataset_version,
            golden_case_id=case.id,
        )
        retrieved_ids = [
            _passage_source_id(p.doc_type, p.anchor, p.source_path)
            for p in response.passages
        ]

        recall5 = recall_at_k(retrieved_ids, case.expected_sources, 5)
        mrr10 = mrr(retrieved_ids[:10], case.expected_sources)
        ndcg10 = ndcg_at_k(retrieved_ids, case.expected_sources, 10)
        citation = citation_accuracy(response.text, case.expected_sources)
        exact = answer_exactness(response.text, case.expected_keywords, case.forbidden_keywords)
        case_regions = sorted({p.region for p in response.passages if p.region})

        recall5_values.append(recall5)
        mrr10_values.append(mrr10)
        ndcg10_values.append(ndcg10)
        citation_values.append(citation)
        exactness_values.append(exact)
        latencies.append(float(response.latency_ms))
        refusal_answers.append(response.text)
        refusal_expecteds.append(case.answer_must_refuse)
        passage_regions.append(case_regions)

        rows.append(
            {
                "id": case.id,
                "question": case.question,
                "intent": response.intent,
                "region_detected": response.region_detected,
                "expected_region": case.expected_region,
                "passage_regions": case_regions,
                "expected_sources": case.expected_sources,
                "retrieved_ids_top10": retrieved_ids[:10],
                "recall@5": round(recall5, 4),
                "mrr@10": round(mrr10, 4),
                "ndcg@10": round(ndcg10, 4),
                "citation_accuracy": round(citation, 4),
                "answer_exactness": round(exact, 4),
                "latency_ms": round(float(response.latency_ms), 2),
            }
        )

    p50 = statistics.median(latencies) if latencies else 0.0
    p95 = _percentile(latencies, 95.0) if latencies else 0.0

    return {
        "cases": len(cases),
        "metrics": {
            "recall@5": _mean(recall5_values),
            "mrr@10": _mean(mrr10_values),
            "ndcg@10": _mean(ndcg10_values),
            "citation_accuracy": _mean(citation_values),
            "refusal_rate": refusal_rate(refusal_answers, refusal_expecteds),
            "fallback_guardrail_success": fallback_guardrail_success(
                refusal_answers,
                refusal_expecteds,
            ),
            "regional_compliance": regional_compliance(passage_regions),
            "answer_exactness": _mean(exactness_values),
            "latency_p50_ms": round(p50, 2),
            "latency_p95_ms": round(p95, 2),
        },
        "rows": rows,
    }


def _passage_source_id(doc_type: str, anchor: str, source_path: str) -> str:
    if anchor:
        return f"{doc_type}::{anchor}"
    return source_path


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * (p / 100.0)
    low = int(idx)
    high = min(low + 1, len(ordered) - 1)
    frac = idx - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac
