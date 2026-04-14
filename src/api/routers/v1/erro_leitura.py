"""Erro de leitura intelligence endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import AuthenticatedUser, get_erro_leitura_service
from src.api.schemas.erro_leitura import (
    ErroLeituraClassificarRequest,
    ErroLeituraClassificarResponse,
    ErroLeituraHotspotResponse,
    ErroLeituraOrdemResponse,
    ErroLeituraPadraoResponse,
)

router = APIRouter()


@router.post("/classificar", response_model=ErroLeituraClassificarResponse)
async def classificar_erro_leitura(
    payload: ErroLeituraClassificarRequest,
    _: AuthenticatedUser,
    service: Annotated[object, Depends(get_erro_leitura_service)],
) -> ErroLeituraClassificarResponse:
    return await service.classificar(payload.texto, payload.devolutiva)


@router.get("/padroes", response_model=list[ErroLeituraPadraoResponse])
async def listar_padroes(
    _: AuthenticatedUser,
    service: Annotated[object, Depends(get_erro_leitura_service)],
    periodo_inicio: date | None = None,
    periodo_fim: date | None = None,
) -> list[ErroLeituraPadraoResponse]:
    return await service.padroes(periodo_inicio, periodo_fim)


@router.get("/hotspots", response_model=list[ErroLeituraHotspotResponse])
async def listar_hotspots(
    _: AuthenticatedUser,
    service: Annotated[object, Depends(get_erro_leitura_service)],
    regiao: str | None = None,
    dt_ini: date | None = None,
    dt_fim: date | None = None,
) -> list[ErroLeituraHotspotResponse]:
    return await service.hotspots(regiao, dt_ini, dt_fim)


@router.get("/{ordem}", response_model=ErroLeituraOrdemResponse)
async def buscar_ordem(
    ordem: str,
    _: AuthenticatedUser,
    service: Annotated[object, Depends(get_erro_leitura_service)],
) -> ErroLeituraOrdemResponse:
    return await service.buscar_ordem(ordem)
