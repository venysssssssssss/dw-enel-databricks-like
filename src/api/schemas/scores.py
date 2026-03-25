"""Schemas for score endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from src.api.schemas.common import HierarchyFilter


class ScoreFilters(HierarchyFilter):
    data_scoring: date | None = None
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ScoreExplanation(BaseModel):
    feature_name: str
    shap_value: float
    direction: str


class ScoreAtrasoResponse(BaseModel):
    cod_nota: int
    score_atraso: float
    classe_predita: str | None = None
    dias_atraso_pred: float | None = None
    model_version: str | None = None
    data_scoring: date | None = None


class ScoreAtrasoDetailResponse(ScoreAtrasoResponse):
    explanations: list[ScoreExplanation] = Field(default_factory=list)


class ScoreInadimplenciaResponse(BaseModel):
    cod_fatura: int
    score_inadimplencia: float
    segmento_risco: str


class ScoreMetaResponse(BaseModel):
    cod_base: int
    projecao_pct: float
    flag_risco: bool


class AnomaliaResponse(BaseModel):
    entidade_id: str
    anomaly_score: float
    is_anomaly: bool
