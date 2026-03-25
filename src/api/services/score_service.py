"""Service for score retrieval."""

from __future__ import annotations

import json
from typing import Any

from src.api.schemas.common import PaginatedResponse, PaginationParams
from src.api.schemas.scores import (
    AnomaliaResponse,
    ScoreAtrasoDetailResponse,
    ScoreAtrasoResponse,
    ScoreFilters,
    ScoreInadimplenciaResponse,
    ScoreMetaResponse,
)


class ScoreService:
    TABLE_BY_DOMAIN = {
        "atraso": "gold.score_atraso_entrega",
        "inadimplencia": "gold.score_inadimplencia",
        "metas": "gold.score_metas",
        "anomalias": "gold.score_anomalias",
    }

    def __init__(self, trino) -> None:
        self.trino = trino

    async def get_scores_atraso(
        self,
        filters: ScoreFilters,
        pagination: PaginationParams,
    ) -> PaginatedResponse[ScoreAtrasoResponse]:
        query = self._build_list_query(self.TABLE_BY_DOMAIN["atraso"], filters, pagination)
        rows = await self.trino.execute(query)
        data = [ScoreAtrasoResponse(**row) for row in rows]
        return PaginatedResponse(data=data, total=len(data), page=pagination.page, page_size=pagination.page_size)

    async def get_score_atraso_detail(self, cod_nota: int) -> ScoreAtrasoDetailResponse:
        query = f"select * from {self.TABLE_BY_DOMAIN['atraso']} where cod_nota = {cod_nota}"
        rows = await self.trino.execute(query)
        if rows:
            row = dict(rows[0])
            row["explanations"] = self._parse_explanations(row.get("explanations"))
            return ScoreAtrasoDetailResponse(**row)
        return ScoreAtrasoDetailResponse(cod_nota=cod_nota, score_atraso=0.0)

    async def get_scores_generic(
        self,
        domain: str,
        response_model: type[Any],
        filters: ScoreFilters,
        pagination: PaginationParams,
    ) -> PaginatedResponse[Any]:
        query = self._build_list_query(self.TABLE_BY_DOMAIN[domain], filters, pagination)
        rows = await self.trino.execute(query)
        data = [response_model(**row) for row in rows]
        return PaginatedResponse(data=data, total=len(data), page=pagination.page, page_size=pagination.page_size)

    def _build_list_query(
        self,
        table: str,
        filters: ScoreFilters,
        pagination: PaginationParams,
    ) -> str:
        score_column = self._score_column(table)
        conditions = [f"{score_column} >= {filters.min_score}"]
        if filters.data_scoring is not None:
            conditions.append(f"data_scoring = date '{filters.data_scoring}'")
        hierarchy_columns = {
            "distribuidora": "cod_distribuidora",
            "ut": "cod_ut",
            "co": "cod_co",
            "base": "cod_base",
        }
        for field_name, column_name in hierarchy_columns.items():
            value = getattr(filters, field_name)
            if value is not None:
                conditions.append(f"{column_name} = {int(value)}")
        return (
            f"select * from {table} where {' and '.join(conditions)} "
            f"order by {score_column} desc limit {pagination.page_size} "
            f"offset {(pagination.page - 1) * pagination.page_size}"
        )

    def _score_column(self, table: str) -> str:
        if table.endswith("score_atraso_entrega"):
            return "score_atraso"
        if table.endswith("score_inadimplencia"):
            return "score_inadimplencia"
        if table.endswith("score_metas"):
            return "projecao_pct"
        return "anomaly_score"

    def _parse_explanations(self, raw_value: Any) -> list[dict[str, Any]]:
        if raw_value is None:
            return []
        if isinstance(raw_value, list):
            return [dict(item) for item in raw_value]
        if isinstance(raw_value, str):
            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError:
                return []
            if isinstance(parsed, list):
                return [dict(item) for item in parsed]
        return []


SCORE_RESPONSE_BY_DOMAIN = {
    "inadimplencia": ScoreInadimplenciaResponse,
    "metas": ScoreMetaResponse,
    "anomalias": AnomaliaResponse,
}
