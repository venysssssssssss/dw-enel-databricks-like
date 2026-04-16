"""RAG API routes shared by the React SPA."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.services.rag_stream import RagStreamRequest, stream_rag_events
from src.data_plane import DataStore
from src.rag.telemetry import log_feedback

router = APIRouter()


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
    body: RagStreamBody,
    x_dataset_version: Annotated[str | None, Header(alias="X-Dataset-Version")] = None,
) -> StreamingResponse:
    current = DataStore().version().hash
    if x_dataset_version and x_dataset_version != current:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Dataset desatualizado no cliente; atualize antes de consultar o chat.",
                "current_dataset_version": current,
            },
        )
    request = RagStreamRequest(
        question=body.question,
        history=body.history,
        context_hint=body.context_hint,
        dataset_version=current,
    )
    return StreamingResponse(
        stream_rag_events(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/rag/feedback")
def rag_feedback(body: FeedbackBody) -> dict[str, bool]:
    from src.rag.config import load_rag_config

    config = load_rag_config()
    log_feedback(
        config.feedback_path,
        question_hash=body.question_hash,
        rating=body.rating,
        comment=body.comment,
    )
    return {"ok": True}
