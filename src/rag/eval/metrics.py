"""Métricas de avaliação para RAG regional CE/SP."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_CITATION_RE = re.compile(r"\[fonte:\s*([^\]]+)\]", re.IGNORECASE)
_REFUSAL_RE = re.compile(
    (
        r"(apenas sobre as regionais|somente ce e sp|"
        r"não encontrei essa informação|não há dados indexados)"
    ),
    re.IGNORECASE,
)


def recall_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    if not expected_ids:
        return 1.0
    expected = {item.lower() for item in expected_ids}
    top = {item.lower() for item in retrieved_ids[: max(k, 1)]}
    return len(expected & top) / len(expected)


def mrr(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    if not expected_ids:
        return 1.0
    expected = {item.lower() for item in expected_ids}
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid.lower() in expected:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], expected_ids: list[str], k: int) -> float:
    if not expected_ids:
        return 1.0
    expected = {item.lower() for item in expected_ids}
    window = retrieved_ids[: max(k, 1)]
    dcg = 0.0
    for idx, rid in enumerate(window, start=1):
        rel = 1.0 if rid.lower() in expected else 0.0
        dcg += rel / math.log2(idx + 1)
    ideal_hits = min(len(expected), len(window))
    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def citation_accuracy(answer_text: str, expected_sources: list[str]) -> float:
    citations = [match.strip().lower() for match in _CITATION_RE.findall(answer_text)]
    if not expected_sources:
        return 1.0 if not citations else 0.0
    if not citations:
        return 0.0
    matched = 0
    for expected in expected_sources:
        exp = expected.strip().lower()
        if any(exp in citation or citation in exp for citation in citations):
            matched += 1
    return matched / len(expected_sources)


def refusal_rate(answers: list[str], expected_refusal_flags: list[bool]) -> float:
    if not answers:
        return 0.0
    correct = 0
    for answer, expected in zip(answers, expected_refusal_flags, strict=False):
        predicted = bool(_REFUSAL_RE.search(answer))
        if predicted == expected:
            correct += 1
    return correct / max(1, len(expected_refusal_flags))


def regional_compliance(
    passages_region: Iterable[Iterable[str] | str],
    allowed: set[str] | None = None,
) -> float:
    allowed_regions = allowed or {"CE", "SP", "CE+SP"}
    rows = list(passages_region)
    if not rows:
        return 1.0
    compliant = 0
    for item in rows:
        regions = [item] if isinstance(item, str) else list(item)
        if all(region in allowed_regions for region in regions):
            compliant += 1
    return compliant / len(rows)


def answer_exactness(
    answer: str,
    expected_keywords: list[str],
    forbidden_keywords: list[str],
) -> float:
    text = answer.lower()
    if expected_keywords:
        expected_hit = (
            sum(1 for kw in expected_keywords if kw.lower() in text) / len(expected_keywords)
        )
    else:
        expected_hit = 1.0
    if forbidden_keywords:
        forbidden_hit = (
            sum(1 for kw in forbidden_keywords if kw.lower() in text) / len(forbidden_keywords)
        )
    else:
        forbidden_hit = 0.0
    return max(0.0, min(1.0, (expected_hit + (1.0 - forbidden_hit)) / 2.0))
