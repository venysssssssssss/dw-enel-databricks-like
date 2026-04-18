from __future__ import annotations

from typing import TYPE_CHECKING

from src.rag.config import RagConfig
from src.rag.orchestrator import detect_regional_scope
from src.rag.retriever import HybridRetriever, route_doc_types
from src.rag.safety import is_out_of_regional_scope

if TYPE_CHECKING:
    from pathlib import Path


def _config(tmp_path: Path) -> RagConfig:
    return RagConfig(
        provider="stub",
        model_repo="",
        model_file="",
        model_path=None,
        embedding_model="stub",
        regional_scope="CE+SP",
        prompt_version="2.0.0",
        chromadb_path=tmp_path / "chroma",
        collection_name="test",
        max_turn_tokens=2000,
        max_context_tokens=3000,
        rerank_enabled=False,
        rerank_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        stream=False,
        retrieval_k=8,
        rerank_top_n=5,
        query_expansion_enabled=True,
        similarity_threshold=0.25,
        corpus_roots=(tmp_path,),
        chunk_size_tokens=200,
        chunk_overlap_tokens=20,
        n_threads=2,
        n_ctx=2048,
        temperature=0.2,
        top_p=0.9,
        api_key=None,
        telemetry_path=tmp_path / "telemetry.jsonl",
        feedback_path=tmp_path / "feedback.csv",
        llm_judge_enabled=False,
    )


class _CollectionStub:
    def __init__(self) -> None:
        self.last_where: dict | None = None

    def query(self, *, query_embeddings, n_results, where):  # noqa: ANN001
        del query_embeddings, n_results
        self.last_where = where
        return {
            "ids": [["c1"]],
            "documents": [["texto de teste"]],
            "metadatas": [[{"source_path": "docs/x.md", "anchor": "a", "doc_type": "data"}]],
            "distances": [[0.1]],
        }


def _make_ready_retriever(tmp_path: Path) -> tuple[HybridRetriever, _CollectionStub]:
    retriever = HybridRetriever(_config(tmp_path))
    collection = _CollectionStub()
    retriever._collection = collection  # type: ignore[attr-defined]
    retriever._embed_fn = lambda texts: [[0.1] * 8 for _ in texts]  # type: ignore[attr-defined]
    return retriever, collection


def test_detect_regional_scope_variants() -> None:
    assert detect_regional_scope("quantas ordens no Ceará?") == "CE"
    assert detect_regional_scope("dados de São Paulo") == "SP"
    assert detect_regional_scope("compare CE e SP") == "CE+SP"
    assert detect_regional_scope("o que é ACF?") is None


def test_is_out_of_regional_scope() -> None:
    assert is_out_of_regional_scope("E no Rio de Janeiro?") is True
    assert is_out_of_regional_scope("E no Rio de Janeiro e CE?") is False
    assert is_out_of_regional_scope("Qual a taxa em SP?") is False


def test_route_doc_types_adds_regional_hints() -> None:
    assert route_doc_types("Quantas ordens no CE?") == ["data", "business", "viz"]
    assert route_doc_types("Taxa em São Paulo") == ["data", "business", "viz"]


def test_retriever_where_clause_for_ce(tmp_path: Path) -> None:
    retriever, collection = _make_ready_retriever(tmp_path)
    retriever.retrieve("q", k=3, doc_types=["data"], dataset_version="v1", region="CE")
    assert collection.last_where == {
        "$and": [
            {"doc_type": {"$in": ["data"]}},
            {"dataset_version": "v1"},
            {"region": {"$in": ["CE", "CE+SP"]}},
        ]
    }


def test_retriever_where_clause_for_sp(tmp_path: Path) -> None:
    retriever, collection = _make_ready_retriever(tmp_path)
    retriever.retrieve("q", region="SP")
    assert collection.last_where == {"region": {"$in": ["SP", "CE+SP"]}}


def test_retriever_where_clause_for_ce_sp(tmp_path: Path) -> None:
    retriever, collection = _make_ready_retriever(tmp_path)
    retriever.retrieve("q", region="CE+SP")
    assert collection.last_where == {"region": {"$in": ["CE", "SP", "CE+SP"]}}


def test_retriever_without_region_filter(tmp_path: Path) -> None:
    retriever, collection = _make_ready_retriever(tmp_path)
    retriever.retrieve("q", doc_types=["business"])
    assert collection.last_where == {"doc_type": {"$in": ["business"]}}
