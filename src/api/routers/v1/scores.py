"""Score endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import AuthenticatedUser, get_score_service
from src.api.schemas.common import PaginatedResponse, PaginationParams
from src.api.schemas.scores import (
    AnomaliaResponse,
    ScoreAtrasoDetailResponse,
    ScoreAtrasoResponse,
    ScoreFilters,
    ScoreInadimplenciaResponse,
    ScoreMetaResponse,
)
from src.api.services.score_service import SCORE_RESPONSE_BY_DOMAIN

router = APIRouter()


async def build_score_filters(
    data_scoring: date | None = None,
    min_score: float = 0.0,
    distribuidora: int | None = None,
    ut: int | None = None,
    co: int | None = None,
    base: int | None = None,
) -> ScoreFilters:
    return ScoreFilters(
        data_scoring=data_scoring,
        min_score=min_score,
        distribuidora=distribuidora,
        ut=ut,
        co=co,
        base=base,
    )


async def build_pagination_params(page: int = 1, page_size: int = 50) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


@router.get("/atraso", response_model=PaginatedResponse[ScoreAtrasoResponse])
async def get_scores_atraso(
    _: AuthenticatedUser,
    filters: Annotated[ScoreFilters, Depends(build_score_filters)],
    pagination: Annotated[PaginationParams, Depends(build_pagination_params)],
    score_service=Depends(get_score_service),
):
    return await score_service.get_scores_atraso(filters, pagination)


@router.get("/atraso/{cod_nota}", response_model=ScoreAtrasoDetailResponse)
async def get_score_atraso_detail(
    cod_nota: int,
    _: AuthenticatedUser,
    score_service=Depends(get_score_service),
):
    return await score_service.get_score_atraso_detail(cod_nota)


@router.get("/inadimplencia", response_model=PaginatedResponse[ScoreInadimplenciaResponse])
async def get_scores_inadimplencia(
    _: AuthenticatedUser,
    filters: Annotated[ScoreFilters, Depends(build_score_filters)],
    pagination: Annotated[PaginationParams, Depends(build_pagination_params)],
    score_service=Depends(get_score_service),
):
    return await score_service.get_scores_generic("inadimplencia", SCORE_RESPONSE_BY_DOMAIN["inadimplencia"], filters, pagination)


@router.get("/metas", response_model=PaginatedResponse[ScoreMetaResponse])
async def get_scores_metas(
    _: AuthenticatedUser,
    filters: Annotated[ScoreFilters, Depends(build_score_filters)],
    pagination: Annotated[PaginationParams, Depends(build_pagination_params)],
    score_service=Depends(get_score_service),
):
    return await score_service.get_scores_generic("metas", SCORE_RESPONSE_BY_DOMAIN["metas"], filters, pagination)


@router.get("/anomalias", response_model=PaginatedResponse[AnomaliaResponse])
async def get_anomalias(
    _: AuthenticatedUser,
    filters: Annotated[ScoreFilters, Depends(build_score_filters)],
    pagination: Annotated[PaginationParams, Depends(build_pagination_params)],
    score_service=Depends(get_score_service),
):
    return await score_service.get_scores_generic("anomalias", SCORE_RESPONSE_BY_DOMAIN["anomalias"], filters, pagination)
