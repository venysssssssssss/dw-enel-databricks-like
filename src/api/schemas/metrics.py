"""Schemas for metrics endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class EfetividadeResponse(BaseModel):
    total_notas: int
    efetividade_bruta_pct: float
    efetividade_liquida_pct: float
    taxa_devolucao_pct: float


class AtrasoSummaryResponse(BaseModel):
    total_notas: int
    atraso_medio_dias: float
    taxa_atraso_pct: float


class ProjecaoMetaResponse(BaseModel):
    valor_meta: float
    valor_realizado: float
    pct_atingimento: float
    status_meta: str
