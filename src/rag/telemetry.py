"""Telemetria JSONL para observabilidade do chat RAG.

Nunca grava texto completo do usuário — apenas hash + primeiros 80 chars
(para debugging). Custo é estimado em $0 para llama-cpp local; mantém
campo para comparabilidade caso troque-se o provider.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class TurnTelemetry:
    ts: str
    provider: str
    model: str
    question_hash: str
    question_preview: str
    intent_class: str
    n_passages: int
    prompt_tokens: int
    completion_tokens: int
    cache_hit: bool
    latency_first_token_ms: float
    latency_total_ms: float
    cost_usd_estimated: float = 0.0
    feedback: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def hash_question(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]


def preview(text: str, n: int = 80) -> str:
    return text[:n].replace("\n", " ")


def record(path: Path, turn: TurnTelemetry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(turn), ensure_ascii=False) + "\n")


def log_feedback(path: Path, *, question_hash: str, rating: str, comment: str = "") -> None:
    """Append-only CSV. Valida rating {up, down}."""
    rating = rating.lower().strip()
    if rating not in {"up", "down"}:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    header_needed = not path.exists()
    comment_clean = comment.replace("\n", " ").replace(",", ";")[:300]
    with path.open("a", encoding="utf-8") as fh:
        if header_needed:
            fh.write("timestamp,question_hash,rating,comment\n")
        fh.write(f"{ts},{question_hash},{rating},{comment_clean}\n")
