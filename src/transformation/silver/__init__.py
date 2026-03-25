"""Domain-specific Silver transformers."""

from src.transformation.silver.cadastros import MASTER_TRANSFORMERS
from src.transformation.silver.entregas_fatura import EntregasFaturaSilverTransformer
from src.transformation.silver.metas_operacionais import MetasOperacionaisSilverTransformer
from src.transformation.silver.notas_operacionais import NotasOperacionaisSilverTransformer
from src.transformation.silver.pagamentos import PagamentosSilverTransformer

TRANSFORMER_REGISTRY = {
    "notas_operacionais": NotasOperacionaisSilverTransformer,
    "entregas_fatura": EntregasFaturaSilverTransformer,
    "pagamentos": PagamentosSilverTransformer,
    "metas_operacionais": MetasOperacionaisSilverTransformer,
    **MASTER_TRANSFORMERS,
}
