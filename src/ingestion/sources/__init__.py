"""Source-specific Bronze ingestors."""

from src.ingestion.sources.cadastros import CADASTRO_INGESTORS
from src.ingestion.sources.entregas_fatura import EntregasFaturaIngestor
from src.ingestion.sources.fatura_reclamada_sp import FaturaReclamadaSpIngestor
from src.ingestion.sources.medidor_sp import MedidorSpIngestor
from src.ingestion.sources.metas_operacionais import MetasOperacionaisIngestor
from src.ingestion.sources.notas_operacionais import NotasOperacionaisIngestor
from src.ingestion.sources.pagamentos import PagamentosIngestor

INGESTION_SOURCE_REGISTRY = {
    "notas_operacionais": NotasOperacionaisIngestor,
    "entregas_fatura": EntregasFaturaIngestor,
    "pagamentos": PagamentosIngestor,
    "metas_operacionais": MetasOperacionaisIngestor,
    "medidor_sp": MedidorSpIngestor,
    "fatura_reclamada_sp": FaturaReclamadaSpIngestor,
    **CADASTRO_INGESTORS,
}
