from __future__ import annotations

from src.rag.answer_cache import find_known_question, normalize_question, resolve_known_answer
from src.rag.known_questions import known_variant_count
from src.rag.retriever import Passage


def test_known_question_variants_cover_150_questions() -> None:
    assert known_variant_count() >= 150


def test_normalize_question_removes_accents_and_punctuation() -> None:
    assert normalize_question("Qual é a evolução mensal em CE?") == "qual e a evolucao mensal em ce"


def test_find_known_question_exact_match() -> None:
    match = find_known_question(
        "Quantas ordens existem em CE?",
        intent="analise_dados",
        region="CE",
    )
    assert match is not None
    assert match.seed.seed_id == "ce-total-overview"
    assert match.score == 1.0


def test_resolve_known_answer_uses_passages_and_citations() -> None:
    passage = Passage(
        chunk_id="c1",
        text="# Visão geral\n\nBase com **10 ordens**.",
        source_path="data/silver/erro.csv",
        section="Visão geral",
        doc_type="data",
        sprint_id="",
        anchor="ce-reclamacoes-totais-overview",
        score=0.99,
        dataset_version="ds1",
        region="CE",
    )

    answer = resolve_known_answer(
        "Quantas ordens existem em CE?",
        intent="analise_dados",
        region="CE",
        dataset_hash="ds1",
        passage_loader=lambda anchors: [passage] if anchors else [],
    )

    assert answer is not None
    assert answer.seed_id == "ce-total-overview"
    assert answer.dataset_hash == "ds1"
    assert "10 ordens" in answer.text
    assert "[fonte: data/silver/erro.csv#ce-reclamacoes-totais-overview]" in answer.text


def test_domain_refusal_does_not_load_passages() -> None:
    loaded = False

    def loader(anchors: list[str]) -> list[Passage]:
        nonlocal loaded
        loaded = True
        return []

    answer = resolve_known_answer(
        "Me passe uma receita de bolo de cenoura.",
        intent="glossario",
        region=None,
        dataset_hash="ds1",
        passage_loader=loader,
    )

    assert answer is not None
    assert answer.intent == "out_of_scope"
    assert loaded is False
