"""Schemas for export endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from src.api.schemas.common import ExportFormat, HierarchyFilter


class ExportBaseRequest(HierarchyFilter):
    periodo_inicio: date
    periodo_fim: date


class ExportNotasRequest(ExportBaseRequest):
    classificacao_acf_asf: list[str] = Field(default_factory=list)


class ExportEntregasRequest(ExportBaseRequest):
    flag_dentro_coordenada: bool | None = None


class ExportPagamentosRequest(ExportBaseRequest):
    flag_inadimplente: bool | None = None


class ExportMetasRequest(ExportBaseRequest):
    status_meta: list[str] = Field(default_factory=list)


class ExportEfetividadeRequest(ExportBaseRequest):
    granularidade: str = "base"


class ExportResponse(BaseModel):
    export_id: str
    status: str
    download_url: str
    row_count: int
    format: ExportFormat
