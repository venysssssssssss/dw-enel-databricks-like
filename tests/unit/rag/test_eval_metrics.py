from __future__ import annotations

from src.rag.eval.metrics import (
    answer_exactness,
    citation_accuracy,
    mrr,
    ndcg_at_k,
    recall_at_k,
    refusal_rate,
    regional_compliance,
)


def test_recall_mrr_ndcg_basic() -> None:
    retrieved = ["data::a", "data::b", "data::c"]
    expected = ["data::b", "data::x"]
    assert recall_at_k(retrieved, expected, 2) == 0.5
    assert mrr(retrieved, expected) == 0.5
    assert 0.0 < ndcg_at_k(retrieved, expected, 3) <= 1.0


def test_citation_accuracy() -> None:
    answer = "Valor X [fonte: data/silver.csv#regiao-ce] e Y [fonte: docs/a.md#h1]"
    assert citation_accuracy(answer, ["data/silver.csv#regiao-ce"]) == 1.0
    assert citation_accuracy(answer, ["data::regiao-sp"]) == 0.0


def test_refusal_rate() -> None:
    answers = [
        "Este assistente responde apenas sobre as regionais CE e SP.",
        "Resposta com número e fonte.",
    ]
    expected = [True, False]
    assert refusal_rate(answers, expected) == 1.0


def test_regional_compliance() -> None:
    assert regional_compliance([["CE", "CE+SP"], ["SP"]]) == 1.0
    assert regional_compliance([["CE"], ["RJ"]]) == 0.5


def test_answer_exactness_penalizes_forbidden_keywords() -> None:
    ok = answer_exactness("CE com refaturamento 11,8%", ["CE", "refaturamento"], ["RJ"])
    bad = answer_exactness("CE e também RJ", ["CE"], ["RJ"])
    assert ok > bad
