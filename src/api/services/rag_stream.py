"""Framework-neutral RAG streaming service for FastAPI/SSE."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field

from src.rag.config import load_rag_config
from src.rag.orchestrator import RagOrchestrator


@dataclass(frozen=True, slots=True)
class RagStreamRequest:
    question: str
    history: list[dict[str, str]] = field(default_factory=list)
    context_hint: str | None = None
    dataset_version: str | None = None


def stream_rag_events(request: RagStreamRequest) -> Iterator[str]:
    config = load_rag_config()
    orchestrator = RagOrchestrator(config)
    try:
        for token in orchestrator.stream_answer(
            request.question,
            history=request.history,
            context_hint=request.context_hint,
            dataset_version=request.dataset_version,
        ):
            yield _sse("token", {"text": token})
        yield _sse("done", {"ok": True})
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


def _sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
