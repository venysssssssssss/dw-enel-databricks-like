"""Shared dependencies for FastAPI routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from src.api.auth.jwt import get_current_user
from src.api.infrastructure.trino_client import AsyncTrinoClient
from src.api.services.erro_leitura_service import ErroLeituraService
from src.api.services.export_service import ExportService
from src.api.services.metrics_service import MetricsService
from src.api.services.score_service import ScoreService
from src.common.minio_client import MinIOClient


async def get_trino_client(request: Request) -> AsyncTrinoClient:
    return request.app.state.trino


async def get_minio_client(request: Request) -> MinIOClient:
    return request.app.state.minio


async def get_export_service(
    trino: Annotated[AsyncTrinoClient, Depends(get_trino_client)],
    minio: Annotated[MinIOClient, Depends(get_minio_client)],
) -> ExportService:
    return ExportService(trino=trino, minio=minio)


async def get_score_service(
    trino: Annotated[AsyncTrinoClient, Depends(get_trino_client)],
) -> ScoreService:
    return ScoreService(trino=trino)


async def get_metrics_service(
    trino: Annotated[AsyncTrinoClient, Depends(get_trino_client)],
) -> MetricsService:
    return MetricsService(trino=trino)


async def get_erro_leitura_service(
    trino: Annotated[AsyncTrinoClient, Depends(get_trino_client)],
) -> ErroLeituraService:
    return ErroLeituraService(trino=trino)


AuthenticatedUser = Annotated[dict[str, str], Depends(get_current_user)]
