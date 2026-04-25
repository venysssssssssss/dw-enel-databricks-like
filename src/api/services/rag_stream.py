"""Framework-neutral RAG streaming service for FastAPI/SSE."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

from src.rag.config import load_rag_config
from src.rag.orchestrator import RagOrchestrator

_ORCHESTRATOR_LOCK = Lock()
_GLOBAL_ORCHESTRATOR: RagOrchestrator | None = None


@dataclass(frozen=True, slots=True)
class RagStreamRequest:
    question: str
    history: list[dict[str, str]] = field(default_factory=list)
    context_hint: str | None = None
    dataset_version: str | None = None


def get_rag_orchestrator(*, app: Any | None = None) -> RagOrchestrator:
    """Retorna orquestrador singleton (app state preferencial, fallback global)."""
    state = getattr(app, "state", None) if app is not None else None
    current = getattr(state, "rag_orchestrator", None) if state is not None else None
    if isinstance(current, RagOrchestrator):
        return current

    global _GLOBAL_ORCHESTRATOR
    if _GLOBAL_ORCHESTRATOR is not None:
        return _GLOBAL_ORCHESTRATOR

    with _ORCHESTRATOR_LOCK:
        if _GLOBAL_ORCHESTRATOR is None:
            config = load_rag_config()
            _GLOBAL_ORCHESTRATOR = RagOrchestrator(config)
        return _GLOBAL_ORCHESTRATOR


def stream_rag_events(
    request: RagStreamRequest,
    *,
    orchestrator: RagOrchestrator | None = None,
) -> Iterator[str]:
    orchestrator = orchestrator or get_rag_orchestrator()
    yield _sse("runtime", _runtime_payload(orchestrator))
    try:
        for event in orchestrator.stream_events(
            request.question,
            history=request.history,
            context_hint=request.context_hint,
            dataset_version=request.dataset_version,
        ):
            yield _sse(event.event, event.payload)
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


def _sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _runtime_payload(orchestrator: RagOrchestrator) -> dict[str, object]:
    config = orchestrator.config
    provider = orchestrator.provider
    return {
        "provider": getattr(provider, "name", "unknown"),
        "model": getattr(provider, "model", "unknown"),
        "n_threads": getattr(config, "n_threads", None),
        "retrieval_k": getattr(config, "retrieval_k", None),
        "rerank_top_n": getattr(config, "rerank_top_n", None),
        "regional_scope": getattr(config, "regional_scope", None),
    }
