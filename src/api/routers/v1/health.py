"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def health(request: Request) -> dict[str, str]:
    return {
        "status": "ok",
        "trino": "configured" if hasattr(request.app.state, "trino") else "missing",
        "minio": "configured" if hasattr(request.app.state, "minio") else "missing",
    }


@router.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}
