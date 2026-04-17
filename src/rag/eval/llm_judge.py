"""LLM judge opcional para faithfulness.

Mantido simples: só executa quando `RAG_LLM_JUDGE=1`.
"""

from __future__ import annotations

import os


def judge_enabled() -> bool:
    return os.getenv("RAG_LLM_JUDGE", "0").strip() in {"1", "true", "True"}


def score_faithfulness(*, answer: str, passages: list[str]) -> float | None:
    """Heurística leve de fallback quando o judge LLM não está habilitado."""
    if not judge_enabled():
        return None
    if not passages:
        return 0.0
    text = answer.lower()
    evidence_hits = 0
    for snippet in passages:
        needle = snippet[:80].lower().strip()
        if needle and needle in text:
            evidence_hits += 1
    return min(1.0, evidence_hits / max(1, len(passages)))
