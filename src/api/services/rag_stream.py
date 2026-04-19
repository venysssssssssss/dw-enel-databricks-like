"""Framework-neutral RAG streaming service for FastAPI/SSE."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
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
    deadline_sec = _stream_timeout_sec()
    events: queue.Queue[tuple[str, dict[str, object]] | None] = queue.Queue()

    def worker() -> None:
        try:
            for event in orchestrator.stream_events(
                request.question,
                history=request.history,
                context_hint=request.context_hint,
                dataset_version=request.dataset_version,
            ):
                events.put((event.event, event.payload))
        except Exception as exc:
            events.put(("error", {"message": str(exc)}))
        finally:
            events.put(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    deadline = time.monotonic() + deadline_sec
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                yield _sse(
                    "error",
                    {
                        "message": (
                            "A consulta demorou mais que o limite operacional. "
                            "Reformule ou tente pergunta mais específica sobre CE/SP."
                        ),
                        "timeout_sec": deadline_sec,
                    },
                )
                return
            try:
                item = events.get(timeout=min(0.25, remaining))
            except queue.Empty:
                continue
            if item is None:
                return
            event_name, payload = item
            yield _sse(event_name, payload)
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


def _sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_timeout_sec() -> float:
    raw = os.getenv("RAG_STREAM_TOTAL_TIMEOUT_SEC", "60").strip()
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 60.0
