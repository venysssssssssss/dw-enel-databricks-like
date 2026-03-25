# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open-source lakehouse analytics platform for ENEL (energy distributor), replacing Databricks with equivalent open-source tooling. Strategy document: `estrategia_plataforma_analitica_preditiva_enel.docx`.

**Hardware target**: Notebook 16GB RAM DDR4, Intel i7-1185G7 (4c/8t), Intel Iris Xe (no GPU for ML). All services must respect memory limits via Docker profiles.

## Architecture

**Medallion pattern (Bronze → Silver → Gold)** on a lakehouse foundation:

- **Bronze**: Raw ingestion, exact replica with technical metadata (`_run_id`, `_ingested_at`, `_source_hash`, `_partition_date`)
- **Silver**: Typed, normalized, deduplicated. ACF/ASF classification, delay calculations, Haversine distance
- **Gold**: Dimensional model (star schema) via dbt Core. 10 dimensions + 7 fact tables

## Tech Stack

| Role | Tool | Version |
|------|------|---------|
| Object Storage | MinIO | RELEASE.2024+ |
| Table Format | Apache Iceberg | 1.5.x |
| Processing | Apache Spark (local mode) | 3.5.x |
| SQL Analytics | Trino | 440+ |
| Transformations | dbt Core | 1.8+ |
| Orchestration | Apache Airflow (SequentialExecutor) | 2.9+ |
| BI | Apache Superset | 4.0+ |
| ML | MLflow + LightGBM + XGBoost + scikit-learn | - |
| Data Quality | Great Expectations | 1.0+ |
| Catalog | Nessie | 0.80+ |
| Export APIs | FastAPI (Pydantic v2, async, streaming) | 0.115+ |
| Observability | Prometheus + Grafana | - |
| Language | Python | 3.12+ |

## Project Structure

```
src/
  ingestion/       # Bronze layer: BaseIngestor, CSVIngestor, IncrementalIngestor
  transformation/  # Silver layer: BaseSilverTransformer, processors/
  api/             # FastAPI: routers/, schemas/, services/, auth/
  ml/              # ML: features/, models/, scoring/, monitoring/
  quality/         # Great Expectations: expectations, checkpoints
  common/          # Shared: spark_session, minio_client, logging, config
dbt/               # dbt project: models/dimensions, models/marts
airflow/dags/      # 7 DAGs covering full lifecycle
infra/             # Docker Compose, Dockerfiles, service configs
tests/             # unit/ and integration/
docs/              # Technical docs: architecture, business-rules, ml, api, sprints
scripts/           # Setup, seed, sample data generation, smoke tests
```

## Common Commands

```bash
make setup              # Create venv and install dependencies
make dev                # Start dev profile (MinIO, Spark, Trino, Airflow, Nessie, PostgreSQL)
make full               # Start all services including Superset, Grafana, Prometheus
make down               # Stop all services
make test               # Run all tests
make test-unit          # Run unit tests only
make lint               # Run ruff + mypy
make pipeline           # Trigger full pipeline: ingest → transform → quality → dbt → ml
make smoke              # Run end-to-end smoke test
make trino-cli          # Open Trino CLI connected to Gold layer
```

## Business Domain

**Client**: ENEL energy distributor (Brazil). Data/rules in Portuguese.

**Key concepts**: ACF/ASF (risk classification), UT (technical unit), CO (operations center), Base/Polo, UC (consumption unit), Lote (batch). Detailed in `docs/business-rules/`.

**ML Models**:
- Delay prediction: LightGBM (binary + regression)
- Non-payment: XGBoost with calibrated probabilities
- Target projection: LightGBM + Logistic Regression ensemble
- Anomalies: Isolation Forest + Z-Score (unsupervised)

All CPU-only, tree-based. TimeSeriesSplit for validation (never random split).

## Key Principles

- Business rules live in pipelines and dimensional models, never in dashboards
- Every load has `run_id`, metadata, quality tests, and layer reconciliation
- Open-source only — no vendor lock-in
- BI first, ML only when underlying data is stable
- Point-in-time correct feature engineering (no data leakage)
- Spark in local mode with `shuffle.partitions=8` and `driver.memory=4g`

## Documentation Index

- Architecture: `docs/architecture/` (overview, tech stack, hardware sizing, data flow)
- Business Rules: `docs/business-rules/` (glossary, ACF/ASF rules, metrics, data sources)
- ML: `docs/ml/` (model selection, feature engineering, MLOps strategy)
- API: `docs/api/` (FastAPI design, endpoints, schemas)
- Sprints: `docs/sprints/` (12 sprints covering full implementation)
