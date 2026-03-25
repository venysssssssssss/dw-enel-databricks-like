"""Export endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import AuthenticatedUser, get_export_service
from src.api.schemas.common import ExportFormat
from src.api.schemas.exports import (
    ExportEfetividadeRequest,
    ExportEntregasRequest,
    ExportMetasRequest,
    ExportNotasRequest,
    ExportPagamentosRequest,
    ExportResponse,
)

router = APIRouter()


@router.post("/notas", response_model=ExportResponse)
async def export_notas(
    filters: ExportNotasRequest,
    _: AuthenticatedUser,
    export_service=Depends(get_export_service),
    export_format: ExportFormat = Query(default=ExportFormat.CSV),
) -> ExportResponse:
    return await export_service.export_domain("notas", filters, export_format)


@router.post("/entregas", response_model=ExportResponse)
async def export_entregas(
    filters: ExportEntregasRequest,
    _: AuthenticatedUser,
    export_service=Depends(get_export_service),
    export_format: ExportFormat = Query(default=ExportFormat.CSV),
) -> ExportResponse:
    return await export_service.export_domain("entregas", filters, export_format)


@router.post("/pagamentos", response_model=ExportResponse)
async def export_pagamentos(
    filters: ExportPagamentosRequest,
    _: AuthenticatedUser,
    export_service=Depends(get_export_service),
    export_format: ExportFormat = Query(default=ExportFormat.CSV),
) -> ExportResponse:
    return await export_service.export_domain("pagamentos", filters, export_format)


@router.post("/metas", response_model=ExportResponse)
async def export_metas(
    filters: ExportMetasRequest,
    _: AuthenticatedUser,
    export_service=Depends(get_export_service),
    export_format: ExportFormat = Query(default=ExportFormat.CSV),
) -> ExportResponse:
    return await export_service.export_domain("metas", filters, export_format)


@router.post("/efetividade", response_model=ExportResponse)
async def export_efetividade(
    filters: ExportEfetividadeRequest,
    _: AuthenticatedUser,
    export_service=Depends(get_export_service),
    export_format: ExportFormat = Query(default=ExportFormat.CSV),
) -> ExportResponse:
    return await export_service.export_domain("efetividade", filters, export_format)


@router.post("/{domain}/stream")
async def stream_domain(
    domain: str,
    filters: ExportNotasRequest,
    _: AuthenticatedUser,
    export_service=Depends(get_export_service),
    export_format: ExportFormat = Query(default=ExportFormat.CSV),
):
    return await export_service.stream_domain(domain, filters, export_format)
