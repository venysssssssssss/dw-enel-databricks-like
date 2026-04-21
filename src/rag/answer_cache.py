"""Deterministic known-answer cache for high-frequency RAG questions."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable, Literal

from src.rag.known_questions import KNOWN_QUESTION_SEEDS, SEED_VERSION, KnownQuestionSeed
from src.rag.retriever import Passage

KnownRegion = Literal["CE", "SP", "CE+SP"] | None

_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)

DOMAIN_REFUSAL_MESSAGE = (
    "Não encontrei essa informação nos dados indexados de CE/SP. Este assistente "
    "responde sobre reclamações, causas, refaturamento, medidores, dashboards e "
    "regras operacionais das regionais CE e SP."
)
REGIONAL_REFUSAL_MESSAGE = (
    "Este assistente responde apenas sobre as regionais **Ceará (CE)** e "
    "**São Paulo (SP)**. Para outras regiões, consulte o dashboard regional "
    "ou a equipe de dados."
)


@dataclass(frozen=True, slots=True)
class KnownAnswerMatch:
    seed: KnownQuestionSeed
    variant: str
    score: float


@dataclass(frozen=True, slots=True)
class CachedAnswer:
    text: str
    intent: str
    region_detected: KnownRegion
    passages: list[Passage]
    seed_id: str
    score: float
    seed_version: str
    dataset_hash: str | None
    answer_mode: str


def normalize_question(text: str) -> str:
    """Normalize PT-BR questions for exact/fuzzy cache matching."""
    decomposed = unicodedata.normalize("NFKD", text)
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = asciiish.casefold()
    without_punct = _PUNCT_RE.sub(" ", lowered)
    return _SPACE_RE.sub(" ", without_punct).strip()


import json
from pathlib import Path

def _load_dynamic_cache() -> list[dict]:
    # Cache dinâmico do aprendizado contínuo
    path = Path("data/rag/dynamic_cache.jsonl")
    entries = []
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    entries.append(data)
                except Exception: pass
    return entries

def find_known_question(
    question: str,
    *,
    intent: str,
    region: KnownRegion,
) -> KnownAnswerMatch | None:
    normalized = normalize_question(question)
    if not normalized:
        return None

    # Busca no cache dinâmico de semântica aprendida
    for entry in _load_dynamic_cache():
        q_dyn = entry.get("question_preview", "")
        if not q_dyn: continue
        dyn_norm = normalize_question(q_dyn)
        score = SequenceMatcher(None, normalized, dyn_norm).ratio()
        if score >= 0.92: # Alta similaridade semântica / léxica
            # Constrói um KnownQuestionSeed fake baseado no cache dinâmico
            anchors_list = entry.get("anchors", [])
            # O extra["sources"] da telemetria são paths (e.g. data/silver/erro_leitura.csv#anchor)
            # Precisamos extrair só a âncora para o passage_loader
            clean_anchors = tuple(a.split("#")[1] if "#" in a else a for a in anchors_list)
            
            fake_seed = KnownQuestionSeed(
                seed_id=f"dynamic-{hash(q_dyn)}",
                variants=(q_dyn,),
                intent=entry.get("intent", intent),
                region=entry.get("region", region),
                anchors=clean_anchors,
                answer_mode="card_summary",
                min_score=0.92
            )
            return KnownAnswerMatch(fake_seed, q_dyn, score)

    # Fallback pro seed estático (original)
    exact: list[KnownAnswerMatch] = []
    fuzzy: list[KnownAnswerMatch] = []
    for seed in KNOWN_QUESTION_SEEDS:
        if not _seed_scope_matches(seed, intent=intent, region=region):
            continue
        for variant in seed.variants:
            variant_norm = normalize_question(variant)
            if normalized == variant_norm:
                exact.append(KnownAnswerMatch(seed, variant, 1.0))
                continue
            if seed.answer_mode in {"regional_refusal", "domain_refusal"}:
                continue
            score = SequenceMatcher(None, normalized, variant_norm).ratio()
            if score >= seed.min_score:
                fuzzy.append(KnownAnswerMatch(seed, variant, score))
    if exact:
        return exact[0]
    if not fuzzy:
        return None
    fuzzy.sort(key=lambda item: item.score, reverse=True)
    return fuzzy[0]


def resolve_known_answer(
    question: str,
    *,
    intent: str,
    region: KnownRegion,
    dataset_hash: str | None,
    passage_loader: Callable[[list[str]], list[Passage]],
) -> CachedAnswer | None:
    match = find_known_question(question, intent=intent, region=region)
    if match is None:
        return None

    seed = match.seed
    if seed.answer_mode == "regional_refusal":
        return CachedAnswer(
            text=REGIONAL_REFUSAL_MESSAGE,
            intent=seed.intent,
            region_detected=None,
            passages=[],
            seed_id=seed.seed_id,
            score=match.score,
            seed_version=SEED_VERSION,
            dataset_hash=dataset_hash,
            answer_mode=seed.answer_mode,
        )
    if seed.answer_mode == "domain_refusal":
        return CachedAnswer(
            text=DOMAIN_REFUSAL_MESSAGE,
            intent=seed.intent,
            region_detected=None,
            passages=[],
            seed_id=seed.seed_id,
            score=match.score,
            seed_version=SEED_VERSION,
            dataset_hash=dataset_hash,
            answer_mode=seed.answer_mode,
        )

    passages = passage_loader(list(seed.anchors))
    if not passages:
        return None
    text = render_cached_answer(seed, passages)
    return CachedAnswer(
        text=text,
        intent=seed.intent,
        region_detected=seed.region if seed.region is not None else region,
        passages=passages,
        seed_id=seed.seed_id,
        score=match.score,
        seed_version=SEED_VERSION,
        dataset_hash=dataset_hash,
        answer_mode=seed.answer_mode,
    )


def render_cached_answer(seed: KnownQuestionSeed, passages: list[Passage]) -> str:
    blocks: list[str] = []
    for passage in passages[:3]:
        summary = _summary_from_passage(passage)
        if summary:
            blocks.append(summary)
    body = "\n\n".join(_dedupe_preserve_order(blocks)).strip()
    citations = _citations(passages)
    if citations and citations not in body:
        body = f"{body}\n\n{citations}".strip()
    return body or "Encontrei dados relevantes nos cards canônicos do RAG."


def _seed_scope_matches(
    seed: KnownQuestionSeed,
    *,
    intent: str,
    region: KnownRegion,
) -> bool:
    if seed.intent in {"out_of_scope", "out_of_regional_scope"}:
        return intent in {seed.intent, "glossario", "analise_dados"}
    if seed.intent != intent:
        # Several observed analytical prompts are classified as glossary.
        if not (seed.intent == "analise_dados" and intent == "glossario"):
            return False
    if seed.region is None:
        return True
    if region is None:
        return seed.region == "CE+SP"
    return seed.region == region


def _summary_from_passage(passage: Passage) -> str:
    text = passage.text.strip()
    if not text:
        return ""
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    if not blocks:
        return ""
    title = blocks[0]
    details = blocks[1] if len(blocks) > 1 else ""
    if details:
        return f"{title}\n\n{details}".strip()
    return title


def _citations(passages: list[Passage]) -> str:
    seen: set[str] = set()
    lines = ["---", "**Fontes:**"]
    for passage in passages:
        key = f"{passage.source_path}#{passage.anchor}"
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {passage.citation()}")
    return "\n".join(lines) if len(lines) > 2 else ""


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
