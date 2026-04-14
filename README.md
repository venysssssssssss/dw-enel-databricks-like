# dw-enel-databricks-like

Lakehouse analítico open source para ENEL, desenhado para substituir capacidades equivalentes ao Databricks em hardware local limitado (notebook i7 / 16GB / sem GPU).

## Escopo implementado

| Bloco | Sprints | Entregas |
|-------|---------|----------|
| Fundação lakehouse | 01–06 | Bronze/Silver, qualidade, Airflow, bootstrap SQL, dados sintéticos |
| Consumo + ML | 07–12 | Gold em dbt, Superset, FastAPI, feature store, treino/scoring, drift, MLflow/Prometheus/Grafana |
| IA de reclamações | 13 | Ingestão CE+SP, embeddings, BERTopic, classificador, dashboard Streamlit |

## Estrutura

```text
src/{common,ingestion,transformation,quality,api,ml}/
airflow/dags/            # 10 DAGs (ingest → silver → quality → dbt → ml → monitoring)
dbt/models/              # marts dimensionais Gold
infra/                   # compose profiles: dev, full, ml, share
apps/streamlit/          # dashboards
scripts/                 # setup, seed, scoring, drift
tests/{unit,integration}/
docs/                    # arquitetura, API, ML, sprints, runbook
```

## Início rápido

```bash
cp .env.example .env
make setup
make sample-data
make features
make lint && make test
```

Stack local mínima:

```bash
make dev
python -m scripts.setup_minio_buckets
```

Stack completa (BI + ML + observabilidade):

```bash
make setup-all
make full
make ml
python -m scripts.setup_mlflow
```

## Comandos principais

<!-- AUTO-GENERATED:MAKE-TARGETS-SHORT -->
| Comando | Descrição |
|---------|-----------|
| `make setup` / `make setup-all` | Cria venv com extras `dev` (ou todos) |
| `make dev` / `make full` / `make ml` | Sobe perfis Docker |
| `make down` | Derruba stack dev |
| `make test` / `make test-unit` / `make test-integration` | Testes |
| `make lint` / `make format` | ruff + mypy |
| `make pipeline` / `make sample-data` / `make seed-time` | Geração de dados |
| `make features` / `make train` / `make score` / `make drift` | Ciclo ML |
| `make erro-leitura-{dry-run,normalize,train,dashboard}` | Sprint 13 — erro de leitura |
| `make share-{up,url,logs,down}` | Exposição pública do dashboard |
<!-- /AUTO-GENERATED:MAKE-TARGETS-SHORT -->

Lista completa e detalhada: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Setup dev, comandos, extras, fluxo PR |
| [docs/ENV.md](docs/ENV.md) | Variáveis de ambiente (core, MinIO, Trino, Spark, ML, auth) |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Deploy, health checks, rollback, troubleshooting |
| [docs/SHARE_DASHBOARD.md](docs/SHARE_DASHBOARD.md) | Exposição pública via Caddy + Cloudflare Tunnel |
| [docs/architecture/](docs/architecture/) | Overview, stack, hardware sizing, data flow |
| [docs/business-rules/](docs/business-rules/) | Glossário ENEL, regras ACF/ASF, métricas |
| [docs/api/](docs/api/) | Design FastAPI, endpoints, schemas |
| [docs/ml/](docs/ml/) | Modelos, feature engineering, MLOps |
| [docs/sprints/](docs/sprints/) | Planos e status de todas as sprints |

## Princípios

- Medallion estrito (Bronze → Silver → Gold); regras de negócio em pipelines, nunca em dashboards.
- `run_id`, metadata técnica e reconciliação de camada em todo load.
- Open-source only — sem vendor lock-in.
- BI antes de ML; ponto-no-tempo correto em features.
- Spark em local mode (`shuffle.partitions=8`, `driver.memory=4g`).
