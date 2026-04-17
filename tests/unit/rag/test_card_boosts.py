"""Testes dos boosts determinísticos de cards e da recusa para cliente individual."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.common.llm_gateway import StubProvider
from src.rag.config import RagConfig
from src.rag.orchestrator import (
    INDIVIDUAL_CLIENT_MESSAGE,
    RagOrchestrator,
    detect_card_boosts,
    is_individual_client_query,
)
from src.rag.retriever import Passage

if TYPE_CHECKING:
    from pathlib import Path


def _make_config(tmp_path: Path) -> RagConfig:
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
        similarity_threshold=0.05,
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


class _FakeRetriever:
    """Retriever falso que simula respostas semânticas e busca por anchor."""

    def __init__(self, semantic: list[Passage], by_anchor: dict[str, Passage]):
        self._semantic = semantic
        self._by_anchor = by_anchor

    def top_passages(self, query: str, *, top_n: int, **_: object) -> list[Passage]:
        return self._semantic[:top_n]

    def get_by_anchors(self, anchors: list[str], **_: object) -> list[Passage]:
        return [self._by_anchor[a] for a in anchors if a in self._by_anchor]


def _passage(anchor: str, score: float = 0.15, doc_type: str = "data") -> Passage:
    return Passage(
        chunk_id=f"id-{anchor}",
        text=f"texto do card {anchor}",
        source_path="data/silver/erro_leitura_normalizado.csv",
        section=anchor,
        doc_type=doc_type,
        sprint_id="",
        anchor=anchor,
        score=score,
        dataset_version="v1",
        region="CE+SP",
        scope="regional",
        data_source="silver.erro_leitura_normalizado",
    )


@pytest.mark.parametrize(
    "question,expected_head",
    [
        ("Qual a causa-raiz mais frequente?", "top-causas-raiz"),
        ("Qual o principal motivo de reclamação?", "top-causas-raiz"),
        ("Quais reclamações possuem maior taxa de refaturamento?", "refaturamento"),
        ("Quais reclamações mais se repetem no tempo?", "evolucao-mensal"),
        ("Compare CE e SP", "ce-vs-sp-causas"),
        ("Qual a diferença entre CE e SP?", "ce-vs-sp-causas"),
        ("Qual o assunto mais reclamado?", "top-assuntos"),
        ("Distribuição por grupo tarifário", "grupo-tarifario"),
    ],
)
def test_detect_card_boosts_maps_queries_to_canonical_anchors(question: str, expected_head: str):
    boosts = detect_card_boosts(question)
    assert boosts, f"sem boost para: {question!r}"
    assert boosts[0] == expected_head


def test_detect_card_boosts_empty_for_greeting():
    assert detect_card_boosts("Olá, tudo bem?") == []


@pytest.mark.parametrize(
    "question",
    [
        "Qual cliente abre mais reclamações?",
        "Dados do CPF 123.456.789-00",
        "Consumidor com mais ordens",
        "Qual a instalação com mais notas?",
    ],
)
def test_is_individual_client_query(question: str):
    assert is_individual_client_query(question)


@pytest.mark.parametrize(
    "question",
    [
        "Qual a causa mais frequente?",
        "Total de reclamações em CE",
        "Compare CE e SP",
    ],
)
def test_is_individual_client_query_false_for_aggregated(question: str):
    assert not is_individual_client_query(question)


def test_top_passages_forces_boost_cards_to_top(tmp_path: Path):
    """Boost deve promover cards canônicos mesmo quando semantic score é baixo."""
    semantic = [
        _passage("visao-geral", score=0.22, doc_type="data"),
        _passage("grupo-tarifario", score=0.18, doc_type="data"),
    ]
    by_anchor = {
        "top-causas-raiz": _passage("top-causas-raiz", score=0.99),
        "top-assuntos": _passage("top-assuntos", score=0.99),
    }
    retriever = _FakeRetriever(semantic=semantic, by_anchor=by_anchor)
    cfg = _make_config(tmp_path)
    orch = RagOrchestrator(cfg, retriever=retriever, provider=StubProvider())  # type: ignore[arg-type]

    passages = orch._top_passages(  # type: ignore[attr-defined]
        "Qual a causa-raiz mais frequente?",
        doc_types=None,
        dataset_version=None,
        region="CE+SP",
    )
    anchors = [p.anchor for p in passages]
    assert anchors[0] == "top-causas-raiz"
    assert "top-assuntos" in anchors
    # Score sintético do boost deve sobrescrever o semântico
    assert passages[0].score >= 0.9


def test_top_passages_dedupes_when_forced_anchor_already_in_semantic(tmp_path: Path):
    duplicated = _passage("top-causas-raiz", score=0.3)
    semantic = [duplicated, _passage("visao-geral", score=0.25)]
    by_anchor = {"top-causas-raiz": duplicated}
    retriever = _FakeRetriever(semantic=semantic, by_anchor=by_anchor)
    cfg = _make_config(tmp_path)
    orch = RagOrchestrator(cfg, retriever=retriever, provider=StubProvider())  # type: ignore[arg-type]

    passages = orch._top_passages(  # type: ignore[attr-defined]
        "Qual a causa-raiz mais frequente?",
        doc_types=None,
        dataset_version=None,
        region="CE+SP",
    )
    # Nenhuma duplicata — chunk_id do forced coincide com semantic
    chunk_ids = [p.chunk_id for p in passages]
    assert len(chunk_ids) == len(set(chunk_ids))


def test_top_passages_respects_regional_filter_on_boosts(tmp_path: Path):
    """Boost de regiao-sp deve ser filtrado quando region=CE."""
    sp_card = Passage(
        chunk_id="id-regiao-sp",
        text="SP",
        source_path="x",
        section="",
        doc_type="data",
        sprint_id="",
        anchor="regiao-sp",
        score=0.99,
        dataset_version="v1",
        region="SP",
        scope="regional",
        data_source="silver",
    )
    ce_card = Passage(
        chunk_id="id-regiao-ce",
        text="CE",
        source_path="x",
        section="",
        doc_type="data",
        sprint_id="",
        anchor="regiao-ce",
        score=0.99,
        dataset_version="v1",
        region="CE",
        scope="regional",
        data_source="silver",
    )
    retriever = _FakeRetriever(
        semantic=[],
        by_anchor={"regiao-sp": sp_card, "regiao-ce": ce_card},
    )
    cfg = _make_config(tmp_path)
    orch = RagOrchestrator(cfg, retriever=retriever, provider=StubProvider())  # type: ignore[arg-type]

    # Query menciona SP explicitamente — mas forçamos region=CE para provar filtro
    orch._top_passages = orch._top_passages  # type: ignore[attr-defined]
    passages = orch._top_passages(  # type: ignore[attr-defined]
        "Qual o principal motivo em SP?",
        doc_types=None,
        dataset_version=None,
        region="CE",
    )
    regions = {p.region for p in passages}
    assert "SP" not in regions  # filtrado
    assert "CE" in regions or not passages


def test_answer_no_longer_refuses_individual_client_query(tmp_path: Path):
    """MVP: perguntas sobre instalação/cliente não são mais recusadas.
    O orchestrator roteia para cards `*-top-instalacoes`.
    """
    cfg = _make_config(tmp_path)
    retriever = _FakeRetriever(semantic=[], by_anchor={})
    orch = RagOrchestrator(cfg, retriever=retriever, provider=StubProvider())  # type: ignore[arg-type]
    resp = orch.answer("Qual cliente abre mais reclamações?")
    assert resp.intent != "individual_client_scope"
    assert resp.text != INDIVIDUAL_CLIENT_MESSAGE


@pytest.mark.parametrize(
    "question,expected_anchor",
    [
        ("Qual a principal causa de reclamação em CE?", "ce-reclamacoes-totais-assuntos"),
        ("Quantas reclamações tem em CE?", "ce-reclamacoes-totais-overview"),
        ("Qual a taxa de refaturamento em CE?", "ce-reclamacoes-totais-refaturamento"),
        ("Como evoluiu o volume em CE ao longo dos meses?", "ce-reclamacoes-totais-evolucao"),
        ("Distribuição por grupo tarifário em CE", "ce-reclamacoes-totais-grupo"),
    ],
)
def test_detect_card_boosts_ce_region_prioritizes_ce_total_cards(
    question: str, expected_anchor: str
):
    boosts = detect_card_boosts(question, region="CE")
    assert expected_anchor in boosts
    # CE-total boosts devem vir antes dos genéricos
    ce_total_positions = [i for i, a in enumerate(boosts) if a.startswith("ce-reclamacoes-totais-")]
    generic_positions = [i for i, a in enumerate(boosts) if not a.startswith("ce-reclamacoes-totais-")]
    if ce_total_positions and generic_positions:
        assert max(ce_total_positions) < min(generic_positions)


def test_detect_card_boosts_without_region_skips_ce_total():
    boosts = detect_card_boosts("Quantas reclamações tem em CE?", region=None)
    assert not any(a.startswith("ce-reclamacoes-totais-") for a in boosts)


@pytest.mark.parametrize(
    "question,expected_anchor",
    [
        ("Qual instalação mais gera reclamações em CE?", "ce-top-instalacoes"),
        ("Qual cliente abre mais reclamações?", "ce-top-instalacoes"),
        ("UC com mais ordens", "ce-top-instalacoes"),
    ],
)
def test_detect_card_boosts_routes_installation_queries(question: str, expected_anchor: str):
    boosts = detect_card_boosts(question)
    assert expected_anchor in boosts


@pytest.mark.parametrize(
    "question",
    [
        "Quais causas em CE em janeiro de 2026?",
        "Principais assuntos em 2026-01",
        "Como foi novembro em CE?",
    ],
)
def test_detect_card_boosts_routes_month_specific_queries(question: str):
    boosts = detect_card_boosts(question)
    assert "ce-reclamacoes-totais-mensal-assuntos" in boosts
    assert "ce-reclamacoes-totais-mensal-causas" in boosts


@pytest.mark.parametrize(
    "question,expected_anchor",
    [
        ("Qual o principal assunto em SP?", "sp-n1-assuntos"),
        ("Evolução mensal de SP", "sp-n1-mensal"),
        ("Quantos tickets em SP?", "sp-n1-overview"),
        ("Qual instalação reclama mais em SP?", "sp-n1-top-instalacoes"),
    ],
)
def test_detect_card_boosts_sp_region_uses_sp_anchors(question: str, expected_anchor: str):
    boosts = detect_card_boosts(question, region="SP")
    assert expected_anchor in boosts


def test_detect_card_boosts_sp_region_skips_ce_total():
    boosts = detect_card_boosts("Qual a principal causa em SP?", region="SP")
    assert not any(a.startswith("ce-reclamacoes-totais-") for a in boosts)


def test_answer_budget_caps_tokens_for_latency_sla(tmp_path: Path):
    cfg = _make_config(tmp_path)
    retriever = _FakeRetriever(semantic=[], by_anchor={})
    orch = RagOrchestrator(cfg, retriever=retriever, provider=StubProvider())  # type: ignore[arg-type]
    # SLA de 35s em CPU ≈ 400 tokens máx
    assert orch._answer_budget() <= 400  # type: ignore[attr-defined]
