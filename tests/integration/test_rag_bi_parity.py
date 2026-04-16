from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pandas as pd

from src.common.llm_gateway import LLMResponse, StubProvider
from src.data_plane import DataStore
from src.rag.config import RagConfig
from src.rag.orchestrator import RagOrchestrator
from src.rag.retriever import Passage

if TYPE_CHECKING:
    from pathlib import Path


class CardRetriever:
    def __init__(self, passages: list[Passage]) -> None:
        self._passages = passages
        self.dataset_version: str | None = None

    def top_passages(
        self,
        query: str,
        *,
        top_n: int | None = None,
        doc_types: list[str] | None = None,
        dataset_version: str | None = None,
    ) -> list[Passage]:
        del query, top_n, doc_types
        self.dataset_version = dataset_version
        return self._passages


class ExtractiveProvider(StubProvider):
    def complete(self, messages, **kwargs):
        del kwargs
        context = messages[1]["content"]
        match = re.search(r"com \*\*(\d+) ordens\*\*", context)
        total = match.group(1) if match else "0"
        return LLMResponse(
            text=f"O KPI exibido no BI é {total} ordens.",
            prompt_tokens=20,
            completion_tokens=10,
            provider=self.name,
            model=self.model,
        )


def _config(tmp_path: Path) -> RagConfig:
    return RagConfig(
        provider="stub",
        model_repo="",
        model_file="",
        model_path=None,
        embedding_model="stub",
        chromadb_path=tmp_path / "chroma",
        collection_name="test",
        max_turn_tokens=2000,
        max_context_tokens=3000,
        rerank_enabled=False,
        stream=False,
        retrieval_k=5,
        rerank_top_n=3,
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
    )


def test_rag_answer_uses_same_dataset_version_and_kpi_as_bi(tmp_path: Path) -> None:
    silver_path = tmp_path / "silver.csv"
    pd.DataFrame(
        [
            {
                "ordem": "1",
                "_source_region": "CE",
                "_data_type": "erro_leitura",
                "dt_ingresso": "2026-01-10",
                "causa_raiz": "Erro de leitura - digitação",
                "texto_completo": "leitura errada por digitacao",
                "flag_resolvido_com_refaturamento": "True",
                "has_causa_raiz_label": "True",
                "instalacao": "100",
                "status": "PROCEDENTE",
                "assunto": "ERRO",
                "grupo": "B",
            }
        ]
    ).to_csv(silver_path, index=False)
    store = DataStore(
        silver_path=silver_path,
        topic_assignments_path=tmp_path / "missing_assignments.csv",
        topic_taxonomy_path=tmp_path / "missing_taxonomy.json",
        cache_dir=tmp_path / "cache",
    )
    version = store.version()
    bi_total = store.aggregate_records("overview")[0]["total_registros"]
    passages = [
        Passage(
            chunk_id=card.chunk_id,
            text=card.text,
            source_path=card.source_path,
            section=card.section,
            doc_type=card.doc_type,
            sprint_id=card.sprint_id,
            anchor=card.anchor,
            score=0.9,
            dataset_version=card.dataset_version,
        )
        for card in store.cards()
        if card.anchor == "visao-geral"
    ]
    retriever = CardRetriever(passages)
    orchestrator = RagOrchestrator(
        _config(tmp_path),
        retriever=retriever,  # type: ignore[arg-type]
        provider=ExtractiveProvider(),
    )

    response = orchestrator.answer(
        "quantas ordens aparecem no BI?",
        dataset_version=version.hash,
    )
    answer_total = int(re.search(r"(\d+) ordens", response.text).group(1))  # type: ignore[union-attr]

    assert retriever.dataset_version == version.hash
    assert answer_total == bi_total
