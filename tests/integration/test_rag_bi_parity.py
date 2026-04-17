from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from src.common.llm_gateway import LLMResponse, StubProvider
from src.data_plane import DataStore
from src.rag.config import RagConfig
from src.rag.orchestrator import RagOrchestrator
from src.rag.retriever import Passage

if TYPE_CHECKING:
    from pathlib import Path


class CardRetriever:
    def __init__(self, cards: list[Passage]) -> None:
        self._cards = cards
        self.dataset_version: str | None = None

    def top_passages(
        self,
        query: str,
        *,
        top_n: int | None = None,
        doc_types: list[str] | None = None,
        dataset_version: str | None = None,
        region: str | None = None,
    ) -> list[Passage]:
        del top_n, doc_types
        self.dataset_version = dataset_version
        q = query.lower()
        if region == "CE":
            target = "regiao-ce"
        elif region == "SP":
            target = "regiao-sp"
        elif "ceará" in q or " ce" in q:
            target = "regiao-ce"
        elif "são paulo" in q or " sp" in q:
            target = "regiao-sp"
        else:
            target = "visao-geral"
        return [card for card in self._cards if card.anchor == target][:1]


class ExtractiveProvider(StubProvider):
    def complete(self, messages, **kwargs):
        del kwargs
        question = messages[-1]["content"].lower()
        context = messages[1]["content"]
        if "taxa" in question:
            match = re.search(r"taxa de refaturamento de \*\*([\d.,]+%)\*\*", context)
            total = match.group(1) if match else "0.0%"
        elif "refaturadas" in question:
            match = re.search(r"Ordens refaturadas: \*\*([\d.]+)\*\*", context)
            total = match.group(1) if match else "0"
        elif "causas rotuladas" in question:
            match = re.search(r"Causas rotuladas: \*\*([\d.]+)\*\*", context)
            total = match.group(1) if match else "0"
        else:
            match = re.search(r"com \*\*([\d.]+) ordens\*\*", context)
            total = match.group(1) if match else "0"
        return LLMResponse(
            text=f"KPI={total}",
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
        regional_scope="CE+SP",
        prompt_version="2.0.0",
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
        llm_judge_enabled=False,
    )


def _normalize_int(value: str) -> float:
    return float(value.strip().replace(".", ""))


def _sample_store(tmp_path: Path) -> DataStore:
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
            },
            {
                "ordem": "2",
                "_source_region": "CE",
                "_data_type": "erro_leitura",
                "dt_ingresso": "2026-02-10",
                "causa_raiz": "Erro de leitura - acesso",
                "texto_completo": "sem acesso",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "True",
                "instalacao": "101",
                "status": "ABERTO",
                "assunto": "ERRO",
                "grupo": "A",
            },
            {
                "ordem": "3",
                "_source_region": "CE",
                "_data_type": "erro_leitura",
                "dt_ingresso": "2026-03-10",
                "causa_raiz": "Erro de leitura - digitação",
                "texto_completo": "outro ce",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "102",
                "status": "ABERTO",
                "assunto": "REFATURAMENTO PRODUTOS",
                "grupo": "B",
            },
            {
                "ordem": "4",
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "dt_ingresso": "2026-02-01",
                "causa_raiz": "ERRO_LEITURA",
                "texto_completo": "sp 1",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "False",
                "instalacao": "200",
                "status": "ABERTO",
                "assunto": "ERRO DE LEITURA",
                "grupo": "B",
            },
            {
                "ordem": "5",
                "_source_region": "SP",
                "_data_type": "base_n1_sp",
                "dt_ingresso": "2026-03-01",
                "causa_raiz": "ERRO_LEITURA",
                "texto_completo": "sp 2",
                "flag_resolvido_com_refaturamento": "False",
                "has_causa_raiz_label": "True",
                "instalacao": "201",
                "status": "ABERTO",
                "assunto": "ERRO DE LEITURA",
                "grupo": "B",
            },
        ]
    ).to_csv(silver_path, index=False)
    return DataStore(
        silver_path=silver_path,
        topic_assignments_path=tmp_path / "missing_assignments.csv",
        topic_taxonomy_path=tmp_path / "missing_taxonomy.json",
        cache_dir=tmp_path / "cache",
    )


@pytest.mark.parametrize(
    ("region", "question", "metric"),
    [
        ("CE", "Quantas ordens existem em CE?", "qtd_ordens"),
        ("CE", "Qual a taxa de refaturamento em CE?", "taxa_refaturamento"),
        ("CE", "Quantas ordens refaturadas existem em CE?", "ordens_refaturadas"),
        ("CE", "Quantas causas rotuladas existem em CE?", "causas_rotuladas"),
        ("SP", "Quantas ordens existem em SP?", "qtd_ordens"),
        ("SP", "Qual a taxa de refaturamento em SP?", "taxa_refaturamento"),
        ("SP", "Quantas ordens refaturadas existem em SP?", "ordens_refaturadas"),
        ("SP", "Quantas causas rotuladas existem em SP?", "causas_rotuladas"),
    ],
)
def test_rag_bi_parity_for_8_kpis(tmp_path: Path, region: str, question: str, metric: str) -> None:
    store = _sample_store(tmp_path)
    version = store.version()
    by_region = store.aggregate_records("by_region", {"regiao": [region]})[0]
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
            region=card.region,
            scope=card.scope,
            data_source=card.data_source,
        )
        for card in store.cards(regional_scope="CE+SP")
    ]
    retriever = CardRetriever(passages)
    orchestrator = RagOrchestrator(
        _config(tmp_path),
        retriever=retriever,  # type: ignore[arg-type]
        provider=ExtractiveProvider(),
    )

    response = orchestrator.answer(question, dataset_version=version.hash)
    raw = re.search(r"KPI=([^\s]+)", response.text).group(1)  # type: ignore[union-attr]

    if metric == "taxa_refaturamento":
        expected = round(float(by_region[metric]) * 100, 1)
        measured = float(raw.strip().replace("%", "").replace(",", "."))
        assert round(measured, 1) == expected
    else:
        expected = float(by_region[metric])
        assert _normalize_int(raw) == expected

    assert retriever.dataset_version == version.hash
