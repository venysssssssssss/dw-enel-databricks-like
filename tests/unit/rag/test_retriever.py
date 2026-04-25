from __future__ import annotations

import pytest

from src.rag.retriever import _align_embedder_to_collection, lexical_overlap, route_doc_types


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


def test_align_embedder_keeps_matching_collection_dimension() -> None:
    collection = _CollectionWithEmbedding(dim=384)

    aligned = _align_embedder_to_collection(collection, _embedder(384))

    assert len(aligned(["q"])[0]) == 384


def test_align_embedder_falls_back_to_hashing_for_legacy_256_collection() -> None:
    collection = _CollectionWithEmbedding(dim=256)

    aligned = _align_embedder_to_collection(collection, _embedder(384))

    assert len(aligned(["q"])[0]) == 256


def test_align_embedder_raises_actionable_error_for_unknown_dimension() -> None:
    collection = _CollectionWithEmbedding(dim=128)

    with pytest.raises(RuntimeError, match="build_rag_corpus.py --rebuild"):
        _align_embedder_to_collection(collection, _embedder(384))


class _CollectionWithEmbedding:
    def __init__(self, *, dim: int) -> None:
        self.dim = dim

    def get(self, *, limit: int, include: list[str]) -> dict[str, list[list[float]]]:
        assert limit == 1
        assert include == ["embeddings"]
        return {"embeddings": [[0.0] * self.dim]}


def _embedder(dim: int):
    def embed(texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] * dim for text in texts]

    return embed
