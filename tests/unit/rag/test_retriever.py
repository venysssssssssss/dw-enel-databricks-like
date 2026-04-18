from __future__ import annotations

from src.rag.retriever import lexical_overlap, route_doc_types


def test_lexical_overlap_basic() -> None:
    assert lexical_overlap("ACF ASF", "regra de ACF e ASF para ordem") > 0
    assert lexical_overlap("foo", "") == 0.0
    assert lexical_overlap("", "bar") == 0.0


def test_lexical_overlap_identical() -> None:
    text = "refaturamento em CE no mês de junho"
    assert lexical_overlap(text, text) == 1.0


def test_route_doc_types_routes_by_keyword() -> None:
    assert route_doc_types("qual a sprint 13?") == ["sprint"]
    assert route_doc_types("o que é ACF") == ["business", "viz"]
    assert route_doc_types("qual a taxonomia consolidada de motivos?") == [
        "data",
        "business",
        "viz",
    ]
    assert route_doc_types("qual modelo lightgbm usa?") == ["ml"]
    assert route_doc_types("endpoint FastAPI /status") == ["api"]
    assert route_doc_types("ingestão bronze com spark") == ["architecture"]
    assert route_doc_types("como filtrar no dashboard?") == ["viz"]


def test_route_doc_types_returns_none_for_generic() -> None:
    assert route_doc_types("bom dia") is None
    assert route_doc_types("me explique tudo") is None
