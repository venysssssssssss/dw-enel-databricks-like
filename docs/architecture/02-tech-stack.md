# Stack Tecnológico Detalhado

## Versões Recomendadas e Justificativas

| Tecnologia | Versão | Justificativa |
|---|---|---|
| Python | 3.12+ | Performance melhorada, typing avançado, melhor async |
| Apache Spark | 3.5.x | Suporte nativo Iceberg, PySpark estável, Spark Connect |
| Apache Iceberg | 1.5.x | REST Catalog nativo, schema evolution madura |
| MinIO | RELEASE.2024+ | S3-compatible, single-node para dev |
| Trino | 440+ | Iceberg connector maduro, performance otimizada |
| dbt Core | 1.8+ | Iceberg adapter, testes integrados |
| Apache Airflow | 2.9+ | TaskFlow API, melhor UI, menos overhead |
| Apache Superset | 4.0+ | Trino connector nativo, filtros melhorados |
| MLflow | 2.15+ | Model Registry v2, melhor tracking |
| FastAPI | 0.115+ | Pydantic v2, lifespan events, OpenAPI 3.1 |
| Great Expectations | 1.0+ | Fluent datasources, checkpoint API simplificada |
| Prometheus | 2.50+ | Scraping otimizado |
| Grafana | 11+ | Dashboards e alertas |
| Nessie | 0.80+ | Catalog com branching |
| Docker | 25+ | Compose v2 nativo |
| Docker Compose | 2.24+ | Profiles para ambiente seletivo |

## Dependências Python Principais

```
# Core Processing
pyspark==3.5.*
pyiceberg==0.7.*
trino[sqlalchemy]==0.328.*

# API
fastapi==0.115.*
uvicorn[standard]==0.30.*
pydantic==2.9.*
pydantic-settings==2.5.*
python-multipart==0.0.12

# ML
lightgbm==4.5.*
xgboost==2.1.*
scikit-learn==1.5.*
mlflow==2.15.*
shap==0.45.*

# Data Quality
great-expectations==1.0.*

# Orchestration
apache-airflow==2.9.*

# dbt
dbt-core==1.8.*
dbt-trino==1.8.*

# Utilities
pandas==2.2.*
polars==1.0.*
pyarrow==17.*
httpx==0.27.*
structlog==24.*
tenacity==9.*
```

## Comunicação entre Componentes

```
Airflow ──trigger──► Spark Jobs (PySpark)
    │                      │
    │                      ▼
    │                MinIO (S3 API)
    │                      │
    │                      ▼
    │                Iceberg Tables
    │                      │
    ├──trigger──► dbt run (via Trino)
    │                      │
    ├──trigger──► Great Expectations
    │                      │
    ├──trigger──► MLflow Training/Scoring
    │
Trino ──reads──► Iceberg Tables (via Nessie Catalog)
    │
Superset ──queries──► Trino (JDBC/SQLAlchemy)
    │
FastAPI ──queries──► Trino (async) / MinIO (direct)
    │
Prometheus ──scrapes──► All services (/metrics)
    │
Grafana ──queries──► Prometheus
```

## Portas dos Serviços (Ambiente Local)

| Serviço | Porta | Protocolo |
|---|---|---|
| MinIO API | 9000 | HTTP/S3 |
| MinIO Console | 9001 | HTTP |
| Spark Master UI | 8080 | HTTP |
| Spark Worker UI | 8081 | HTTP |
| Trino | 8443 | HTTP |
| Airflow Webserver | 8085 | HTTP |
| Superset | 8088 | HTTP |
| MLflow | 5000 | HTTP |
| FastAPI | 8000 | HTTP |
| Nessie | 19120 | HTTP |
| Prometheus | 9090 | HTTP |
| Grafana | 3000 | HTTP |
| Great Expectations Data Docs | 8095 | HTTP |
