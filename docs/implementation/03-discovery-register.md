# Discovery Register — Fontes e Regras

Este registro consolida os pontos de discovery ainda pendentes da Sprint 01 para evitar que o projeto confunda contrato documentado com contrato validado em campo.

## Fontes prioritárias

| Fonte | Contrato técnico | Owner técnico | Owner negócio | Dados reais | Status |
|---|---|---|---|---|---|
| Notas Operacionais | [notas_operacionais.yml](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/config/notas_operacionais.yml) | `TBD` | `TBD` | não anexados | pendente de validação |
| Entregas de Fatura | [entregas_fatura.yml](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/config/entregas_fatura.yml) | `TBD` | `TBD` | não anexados | pendente de validação |
| Pagamentos | [pagamentos.yml](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/config/pagamentos.yml) | `TBD` | `TBD` | não anexados | pendente de validação |
| Cadastros | [src/ingestion/config](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/config) | `TBD` | `TBD` | não anexados | pendente de validação |
| Metas Operacionais | [metas_operacionais.yml](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/config/metas_operacionais.yml) | `TBD` | `TBD` | não anexados | pendente de validação |

## Regras de negócio críticas

| Regra | Implementação atual | Evidência de teste | Validação negócio |
|---|---|---|---|
| Classificação ACF/ASF | [business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/processors/business_rules.py) | [test_business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_business_rules.py) | pendente |
| Cálculo de atraso | [business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/processors/business_rules.py) | [test_business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_business_rules.py) | pendente |
| Haversine / entrega dentro da coordenada | [business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/processors/business_rules.py) | [test_business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_business_rules.py) | pendente |
| Inadimplência > 30 dias | [pagamentos.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/silver/pagamentos.py) | cobertura estrutural | pendente |
| Status de metas | [metas_operacionais.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/silver/metas_operacionais.py) | cobertura estrutural | pendente |
