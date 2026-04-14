"""Schemas for erro de leitura intelligence endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ErroLeituraClassificarRequest(BaseModel):
    texto: str = Field(min_length=3)
    devolutiva: str | None = None


class ClasseProbabilidade(BaseModel):
    classe: str
    probabilidade: float


class ErroLeituraClassificarResponse(BaseModel):
    classe: str
    probabilidade: float
    top3: list[ClasseProbabilidade]


class ErroLeituraPadraoResponse(BaseModel):
    topic_id: int | None = None
    topic_name: str
    quantidade: int
    percentual: float


class ErroLeituraHotspotResponse(BaseModel):
    regiao: str
    classe_erro: str
    data: date | None = None
    qtd_erros: int
    anomaly_score: float
    is_anomaly: bool


class ErroLeituraOrdemResponse(BaseModel):
    ordem: str
    classe: str | None = None
    probabilidade: float | None = None
    causa_raiz: str | None = None
    status: str | None = None
    regiao: str | None = None
    explicacao: list[str] = Field(default_factory=list)
