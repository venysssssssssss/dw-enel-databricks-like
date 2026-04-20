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

    async def get_mis_aconchegante_metrics(self) -> dict:
        try:
            # Em prod chamaria as tabelas dbt Gold
            # rows = await self.trino.execute("select * from gold.agg_mis_macrotemas_mensal")
            # Para fallback, caso a tabela nÃ£o exista (ambiente docker clean), retorna os mocks do front
            pass
        except Exception:
            pass
            
        return {
            "months": ['Abr 25','Mai 25','Jun 25','Jul 25','Ago 25','Set 25','Out 25','Nov 25','Dez 25','Jan 26','Fev 26','Mar 26'],
            "macroTemas": [
                {"name": 'Refaturamento & Cobrança', "qtd": 91891, "pct": 54.9, "delta": +18.2},
                {"name": 'Religação & Multas', "qtd": 22310, "pct": 13.3, "delta": +4.1},
                {"name": 'Geração Distribuída (GD)', "qtd": 16240, "pct": 9.7, "delta": +22.7},
                {"name": 'Ouvidoria & Jurídico', "qtd": 12108, "pct": 7.2, "delta": +3.3},
                {"name": 'Variação de Consumo', "qtd": 9830, "pct": 5.9, "delta": -2.1},
                {"name": 'Faturamento por Média/Estim.', "qtd": 7412, "pct": 4.4, "delta": +41.0},
                {"name": 'Outros', "qtd": 4690, "pct": 2.8, "delta": +1.0},
                {"name": 'Entrega da Fatura', "qtd": 3152, "pct": 1.9, "delta": -5.4},
            ],
            "macroTrend": {
                'Refaturamento & Cobrança': [5400,6200,7300,8200,8800,8400,8100,7900,7400,7100,6800,6200],
                'Religação & Multas': [1200,1800,5400,3200,2600,2200,2000,2100,2400,2600,2100,1800],
                'Geração Distribuída (GD)': [600, 720, 950, 1150,1300,1420,1500,1550,1700,1800,1900,1950],
                'Ouvidoria & Jurídico': [800, 820, 860, 1000,1040,1080,1100,1120,1130,1120,1100,1100],
                'Variação de Consumo': [650, 700, 820, 900, 920, 880, 830, 810, 800, 820, 840, 860],
                'Faturamento por Média/Estim.': [220, 260, 310, 380, 440, 520, 620, 720, 820, 920,1020,1180],
                'Outros': [300, 310, 330, 360, 380, 400, 410, 420, 430, 440, 440, 450],
            },
            "regionMonthly": {
                'CE': [490,510,520,500,470,450,510,460,470,560,600,380],
                'SP': [540,560,580,1080,1180,1220,1440,1340,1380,2180,2627,560]
            },
            "causas": [
                {"name": 'digitacao', "v": 4974, "refat": 0.3, "regiao": 'CE'},
                {"name": 'consumo_elevado_revisao', "v": 3930, "refat": 16.2, "regiao": 'SP'},
                {"name": 'indefinido', "v": 3678, "refat": 0.0, "regiao": 'SP'},
                {"name": 'autoleitura_cliente', "v": 2939, "refat": 9.1, "regiao": 'SP'},
                {"name": 'refaturamento_corretivo', "v": 668, "refat": 3.6, "regiao": 'CE'},
            ],
            "severidade": {
                "CE": {"critical": 29, "high": 5719, "medium": 75, "low": 112},
                "SP": {"critical": 365, "high": 3502, "medium": 4061, "low": 5564}
            },
            "regCausa": [[0,0,4974],[1,0,300],[2,0,250],[3,0,200],[4,0,668],[0,1,100],[1,1,3930],[2,1,3678],[3,1,2939],[4,1,100]],
            "topics": [],
            "categoriasTax": [],
            "reincidencia": {
                "CE": [4780, 360, 48, 12, 4, 1],
                "SP": [10950, 890, 140, 28, 9, 3]
            },
            "quadrant": [{"name":"digitacao","x":4974,"y":0.3,"z":1492.2}],
            "coverage": [],
            "govHeat": [[0,0, 0.12],[1,0,0.22],[2,0,0.07],[3,0,0.02],[0,1, 0.18],[1,1,0.34],[2,1,0.28],[3,1,0.04]]
        }
