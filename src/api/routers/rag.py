"""RAG API routes shared by the React SPA."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.services.rag_stream import (
    RagStreamRequest,
    get_rag_orchestrator,
    stream_rag_events,
)
from src.data_plane import DataStore
from src.rag.telemetry import log_feedback

router = APIRouter()

_DATASET_CACHE_LOCK = Lock()


@dataclass(slots=True)
class _DatasetVersionCache:
    dataset_hash: str = ""
    fingerprint: tuple[tuple[str, int, int], ...] = ()
    ts: float = 0.0


_DATASET_VERSION_CACHE = _DatasetVersionCache()


class RagStreamBody(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list)
    context_hint: str | None = None


class FeedbackBody(BaseModel):
    question_hash: str = Field(min_length=1, max_length=128)
    rating: str = Field(pattern="^(up|down)$")
    comment: str = Field(default="", max_length=300)


@router.get("/rag/cards")
def rag_cards() -> dict[str, Any]:
    store = DataStore()
    cards = store.cards()
    return {
        "dataset_hash": store.version().hash,
        "cards": [
            {
                "id": card.chunk_id,
                "title": card.section,
                "hash": card.dataset_version,
                "anchor": card.anchor,
                "token_count": card.token_count,
            }
            for card in cards
        ],
    }


@router.post("/rag/stream")
def rag_stream(
    http_request: Request,
    body: RagStreamBody,
    x_dataset_version: Annotated[str | None, Header(alias="X-Dataset-Version")] = None,
) -> StreamingResponse:
    store = DataStore()
    current = _current_dataset_hash(store)
    if x_dataset_version and x_dataset_version != current:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Dataset desatualizado no cliente; atualize antes de consultar o chat.",
                "current_dataset_version": current,
            },
        )
    rag_request = RagStreamRequest(
        question=body.question,
        history=body.history,
        context_hint=body.context_hint,
        dataset_version=current,
    )
    orchestrator = get_rag_orchestrator(app=http_request.app)
    return StreamingResponse(
        stream_rag_events(rag_request, orchestrator=orchestrator),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/rag/feedback")
def rag_feedback(body: FeedbackBody) -> dict[str, bool]:
    from src.rag.config import load_rag_config

    config = load_rag_config()
    recorded = log_feedback(
        config.feedback_path,
        question_hash=body.question_hash,
        rating=body.rating,
        comment=body.comment,
    )
    return {"ok": recorded}


def _dataset_cache_ttl_sec() -> float:
    raw = os.getenv("RAG_DATASET_VERSION_CACHE_TTL_SEC", "5").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 5.0


def _store_fingerprint(store: Any) -> tuple[tuple[str, int, int], ...]:
    attrs = (
        "silver_path",
        "topic_assignments_path",
        "topic_taxonomy_path",
        "medidor_sp_path",
        "fatura_sp_path",
    )
    out: list[tuple[str, int, int]] = []
    for attr in attrs:
        path = getattr(store, attr, None)
        if not isinstance(path, Path):
            continue
        if not path.exists():
            continue
        stat = path.stat()
        out.append((str(path), int(stat.st_size), int(stat.st_mtime_ns)))
    out.sort()
    return tuple(out)


def _current_dataset_hash(store: Any) -> str:
    ttl = _dataset_cache_ttl_sec()
    fingerprint = _store_fingerprint(store)
    now = time.monotonic()
    with _DATASET_CACHE_LOCK:
        if (
            _DATASET_VERSION_CACHE.dataset_hash
            and _DATASET_VERSION_CACHE.fingerprint == fingerprint
            and (now - _DATASET_VERSION_CACHE.ts) <= ttl
        ):
            return _DATASET_VERSION_CACHE.dataset_hash

    current = str(store.version().hash)
    with _DATASET_CACHE_LOCK:
        _DATASET_VERSION_CACHE.dataset_hash = current
        _DATASET_VERSION_CACHE.fingerprint = fingerprint
        _DATASET_VERSION_CACHE.ts = now
    return current
