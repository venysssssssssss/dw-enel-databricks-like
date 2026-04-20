# Arquitetura Geral da Plataforma

## Visão Macro

A plataforma segue o padrão **Lakehouse** com camada de **Data Warehouse** dimensional por cima, operando inteiramente com tecnologias open source. O objetivo é replicar capacidades equivalentes ao Databricks sem lock-in de vendor.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE CONSUMO                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Superset  │  │ FastAPI  │  │ Streamlit│  │  Trino   / RAG   │   │
│  │(Dashboards│  │(Exports) │  │(MIS/Chat)│  │(Ad-hoc / Busca)  │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └────────┬─────────┘   │
│        │             │             │                 │              │
├────────┴─────────────┴─────────────┴─────────────────┴──────────────┤
│                        CAMADA GOLD                                  │
│  Data Marts dimensionais: fato + dimensões conformadas              │
│  Materialização: dbt Core sobre Spark/Trino                         │
├─────────────────────────────────────────────────────────────────────┤
│                        CAMADA DE MLOps & GENAI                      │
│  MLflow (Batch Scores), Llama.cpp/Qwen2.5 (LLM Fallback), ChromaDB  │
├─────────────────────────────────────────────────────────────────────┤
│                        CAMADA SILVER                                │
│  Dados tipados, normalizados, deduplicados, historicizados          │
│  Processamento: Apache Spark (PySpark) e Batch Inference (LLM)      │
├─────────────────────────────────────────────────────────────────────┤
│                        CAMADA BRONZE                                │
│  Dados brutos exatamente como chegaram da fonte                     │
│  Metadados: run_id, timestamp_ingestão, hash, origem                │
├─────────────────────────────────────────────────────────────────────┤
│                     ARMAZENAMENTO (MinIO)                           │
│  Object storage S3-compatible                                       │
│  Formato: Apache Iceberg (ACID, time travel, schema evolution)      │
├─────────────────────────────────────────────────────────────────────┤
│                      ORQUESTRAÇÃO (Airflow)                         │
│  Scheduling, encadeamento, monitoramento, retry, alertas            │
├─────────────────────────────────────────────────────────────────────┤
│                    GOVERNANÇA & QUALIDADE                           │
│  Nessie Catalog │ Great Expectations │ OpenMetadata │ OpenLineage   │
├─────────────────────────────────────────────────────────────────────┤
│                     OBSERVABILIDADE                                 │
│  Prometheus + Grafana (métricas, alertas, SLA)                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Fluxo de Dados End-to-End

```
Fontes Operacionais (CSV, API, DB)
        │
        ▼
   [Airflow DAG]
        │
        ├──► Bronze (MinIO/Iceberg) ─── raw, imutável
        │         │
        │         ▼
        ├──► Silver (Spark) ─── limpo, tipado, deduplicado
        │         │
        │         ▼
        ├──► Gold (dbt/Spark) ─── marts dimensionais
        │         │
        │         ├──► Superset (dashboards gerenciais)
        │         ├──► FastAPI (exportação filtrada)
        │         ├──► Trino (consultas ad-hoc)
        │         └──► MLflow (feature store → scoring)
        │
        └──► Great Expectations (testes em cada camada)
```

## Decisões Arquiteturais Chave

### 1. Por que Lakehouse e não DW puro?
- Necessidade de preservar dados brutos para reprocessamento
- Versionamento e time travel (Iceberg) para auditoria
- Flexibilidade para ML sobre dados não-estruturados no futuro
- Schema evolution sem downtime

### 2. Por que Spark local e não cluster?
- Hardware limitado (16GB RAM, i7-1185G7)
- Volume de dados inicial não justifica cluster distribuído
- Spark em modo standalone com driver local atende ao MVP
- Migração para cluster é transparente quando necessário

### 3. Por que dbt Core e não SQL puro?
- Grafo de dependências explícito entre modelos
- Testes integrados (unique, not_null, relationships)
- Documentação auto-gerada
- Versionamento de transformações no Git

### 4. Por que FastAPI e não Flask/Django?
- Performance async nativa (uvicorn/ASGI)
- Validação automática via Pydantic v2
- OpenAPI 3.1 auto-gerado
- Streaming responses para exports grandes
- Type hints nativos do Python

### 5. Por que batch ML e não real-time?
- Dados operacionais têm latência natural (diário/intradiário)
- CPU-only (Intel Iris Xe não serve para inference GPU)
- Modelos tabulares (LightGBM/XGBoost) são rápidos em CPU
- Complexidade operacional muito menor

## Separação de Responsabilidades

| Componente | Responsabilidade | NÃO faz |
|---|---|---|
| MinIO | Armazenamento persistente | Processamento |
| Iceberg | Formato de tabela, versionamento | Queries diretas |
| Spark | Transformação pesada (Bronze→Silver→Gold) | Servir queries de BI |
| Trino | Queries analíticas de leitura | Transformação pesada |
| dbt | Modelagem dimensional (Gold) | Ingestão |
| Airflow | Orquestração e scheduling | Processamento de dados |
| Superset | Visualização e dashboards | Lógica de negócio |
| FastAPI | APIs de exportação e integração | Transformação de dados |
| MLflow | Tracking de experimentos e modelos | Feature engineering |
| Great Expectations | Validação de qualidade | Transformação |
