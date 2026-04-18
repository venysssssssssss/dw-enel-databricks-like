from __future__ import annotations

from typing import TYPE_CHECKING

from src.common.llm_gateway import LLMResponse, StubProvider
from src.rag.config import RagConfig
from src.rag.orchestrator import RagOrchestrator
from src.rag.retriever import Passage

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
        similarity_threshold=0.01,
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


class RegionalRetriever:
    def __init__(self) -> None:
        self.pool = [
            _passage("ce", "CE", "regiao-ce", 0.9, region="CE"),
            _passage("sp", "SP", "regiao-sp", 0.88, region="SP"),
            _passage("mix", "MIX", "ce-vs-sp-causas", 0.86, region="CE+SP"),
            _passage("rj", "RJ", "regiao-rj", 0.99, region="RJ"),
        ]

    def top_passages(
        self,
        query: str,
        *,
        top_n: int | None = None,
        doc_types: list[str] | None = None,
        dataset_version: str | None = None,
        region: str | None = None,
    ) -> list[Passage]:
        del query, top_n, doc_types, dataset_version
        if region == "CE":
            return [p for p in self.pool if p.region in {"CE", "CE+SP"}]
        if region == "SP":
            return [p for p in self.pool if p.region in {"SP", "CE+SP"}]
        if region == "CE+SP":
            return [p for p in self.pool if p.region in {"CE", "SP", "CE+SP"}]
        return list(self.pool)

    def get_by_anchors(self, anchors: list[str], **kwargs) -> list[Passage]:
        del anchors, kwargs
        return []


class EchoProvider(StubProvider):
    def complete(self, messages, **kwargs):  # noqa: ANN001
        del kwargs
        return LLMResponse(
            text="Resposta com citação [fonte: data/silver/erro_leitura_normalizado.csv#regiao-ce]",
            prompt_tokens=30,
            completion_tokens=10,
            provider=self.name,
            model=self.model,
        )


def test_regional_compliance_never_returns_outside_ce_sp(tmp_path: Path) -> None:
    orch = RagOrchestrator(
        _config(tmp_path),
        retriever=RegionalRetriever(),  # type: ignore[arg-type]
        provider=EchoProvider(),
    )
    queries = [
        "Quantas ordens em CE?",
        "Qual taxa em SP?",
        "Compare CE e SP",
        "Qual o total de reclamações?",
        "Quais causas mais frequentes?",
        "Evolução mensal CE+SP",
        "No Ceará, qual assunto principal?",
        "Em São Paulo, qual taxa de refaturamento?",
        "Resumo CE versus SP",
        "Dados de CE por grupo",
    ]
    allowed = {"CE", "SP", "CE+SP"}
    for query in queries:
        response = orch.answer(query)
        assert response.intent != "out_of_regional_scope"
        assert all(p.region in allowed for p in response.passages)


def test_out_of_regional_scope_refuses_without_passages(tmp_path: Path) -> None:
    orch = RagOrchestrator(
        _config(tmp_path),
        retriever=RegionalRetriever(),  # type: ignore[arg-type]
        provider=EchoProvider(),
    )
    response = orch.answer("E no Rio de Janeiro?")
    assert response.intent == "out_of_regional_scope"
    assert response.passages == []


def _passage(
    chunk_id: str,
    section: str,
    anchor: str,
    score: float,
    *,
    region: str,
) -> Passage:
    return Passage(
        chunk_id=chunk_id,
        text=chunk_id,
        source_path="data/silver/erro_leitura_normalizado.csv",
        section=section,
        doc_type="data",
        sprint_id="",
        anchor=anchor,
        score=score,
        region=region,
        scope="regional",
        data_source="silver.erro_leitura_normalizado",
    )
