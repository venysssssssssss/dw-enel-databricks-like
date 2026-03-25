"""Metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import AuthenticatedUser, get_metrics_service
from src.api.schemas.metrics import AtrasoSummaryResponse, EfetividadeResponse, ProjecaoMetaResponse

router = APIRouter()


@router.get("/efetividade", response_model=EfetividadeResponse)
async def get_efetividade(
    _: AuthenticatedUser,
    metrics_service=Depends(get_metrics_service),
) -> EfetividadeResponse:
    return await metrics_service.get_efetividade()


@router.get("/atraso/summary", response_model=AtrasoSummaryResponse)
async def get_atraso_summary(
    _: AuthenticatedUser,
    metrics_service=Depends(get_metrics_service),
) -> AtrasoSummaryResponse:
    return await metrics_service.get_atraso_summary()


@router.get("/metas/projecao", response_model=ProjecaoMetaResponse)
async def get_projecao_meta(
    _: AuthenticatedUser,
    metrics_service=Depends(get_metrics_service),
) -> ProjecaoMetaResponse:
    return await metrics_service.get_projecao_meta()
