"""Services for erro de leitura intelligence endpoints."""

from __future__ import annotations

from datetime import date
from typing import Any

from src.api.schemas.erro_leitura import (
    ClasseProbabilidade,
    ErroLeituraClassificarResponse,
    ErroLeituraHotspotResponse,
    ErroLeituraOrdemResponse,
    ErroLeituraPadraoResponse,
)
from src.ml.models.erro_leitura_classifier import KeywordErroLeituraClassifier


class ErroLeituraService:
    def __init__(self, trino: Any) -> None:
        self.trino = trino
        self.classifier = KeywordErroLeituraClassifier()

    async def classificar(self, texto: str, devolutiva: str | None = None) -> ErroLeituraClassificarResponse:
        payload = self.classifier.classify(" ".join(value for value in [texto, devolutiva or ""] if value))
        return ErroLeituraClassificarResponse(
            classe=str(payload["classe"]),
            probabilidade=float(payload["probabilidade"]),
            top3=[ClasseProbabilidade(**item) for item in payload["top3"]],
        )

    async def padroes(self, periodo_inicio: date | None = None, periodo_fim: date | None = None) -> list[ErroLeituraPadraoResponse]:
        query = self._padroes_query(periodo_inicio, periodo_fim)
        rows = await self.trino.execute(query)
        return [ErroLeituraPadraoResponse(**row) for row in rows]

    async def hotspots(
        self,
        regiao: str | None = None,
        dt_ini: date | None = None,
        dt_fim: date | None = None,
    ) -> list[ErroLeituraHotspotResponse]:
        query = self._hotspots_query(regiao, dt_ini, dt_fim)
        rows = await self.trino.execute(query)
        return [ErroLeituraHotspotResponse(**row) for row in rows]

    async def buscar_ordem(self, ordem: str) -> ErroLeituraOrdemResponse:
        query = f"select * from gold.fato_erro_leitura where ordem = '{_sql_string(ordem)}'"
        rows = await self.trino.execute(query)
        if not rows:
            return ErroLeituraOrdemResponse(ordem=ordem, explicacao=["ordem_nao_encontrada"])
        row = rows[0]
        return ErroLeituraOrdemResponse(
            ordem=str(row.get("ordem", ordem)),
            classe=row.get("classe"),
            probabilidade=row.get("probabilidade"),
            causa_raiz=row.get("causa_raiz"),
            status=row.get("status"),
            regiao=row.get("regiao"),
            explicacao=_coerce_explicacao(row.get("explicacao")),
        )

    def _padroes_query(self, periodo_inicio: date | None, periodo_fim: date | None) -> str:
        conditions = []
        if periodo_inicio is not None:
            conditions.append(f"data >= date '{periodo_inicio}'")
        if periodo_fim is not None:
            conditions.append(f"data <= date '{periodo_fim}'")
        where_clause = f"where {' and '.join(conditions)}" if conditions else ""
        return (
            "select topic_id, topic_name, quantidade, percentual "
            f"from gold.vw_erro_leitura_padroes {where_clause} "
            "order by quantidade desc"
        )

    def _hotspots_query(self, regiao: str | None, dt_ini: date | None, dt_fim: date | None) -> str:
        conditions = []
        if regiao is not None:
            conditions.append(f"regiao = '{_sql_string(regiao.upper())}'")
        if dt_ini is not None:
            conditions.append(f"data >= date '{dt_ini}'")
        if dt_fim is not None:
            conditions.append(f"data <= date '{dt_fim}'")
        where_clause = f"where {' and '.join(conditions)}" if conditions else ""
        return (
            "select regiao, classe_erro, data, qtd_erros, anomaly_score, is_anomaly "
            f"from gold.hotspots_erro_leitura {where_clause} "
            "order by anomaly_score desc"
        )


def _sql_string(value: str) -> str:
    return value.replace("'", "''")


def _coerce_explicacao(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
