"""Service for aggregated metrics."""

from __future__ import annotations

from src.api.schemas.metrics import AtrasoSummaryResponse, EfetividadeResponse, ProjecaoMetaResponse


class MetricsService:
    def __init__(self, trino) -> None:
        self.trino = trino

    async def get_efetividade(self) -> EfetividadeResponse:
        rows = await self.trino.execute("select 0 as total_notas, 0.0 as efetividade_bruta_pct, 0.0 as efetividade_liquida_pct, 0.0 as taxa_devolucao_pct")
        return EfetividadeResponse(**rows[0])

    async def get_atraso_summary(self) -> AtrasoSummaryResponse:
        rows = await self.trino.execute("select 0 as total_notas, 0.0 as atraso_medio_dias, 0.0 as taxa_atraso_pct")
        return AtrasoSummaryResponse(**rows[0])

    async def get_projecao_meta(self) -> ProjecaoMetaResponse:
        rows = await self.trino.execute("select 0.0 as valor_meta, 0.0 as valor_realizado, 0.0 as pct_atingimento, 'NAO_ATINGIDA' as status_meta")
        return ProjecaoMetaResponse(**rows[0])
