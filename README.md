# dw-enel-databricks-like

Lakehouse analítico open source para ENEL, desenhado para substituir capacidades equivalentes ao Databricks em hardware local limitado.

## Escopo implementado

Esta base materializa as sprints `01-12` em dois níveis:

- `01-06`: fundação do lakehouse local com Bronze, Silver, qualidade, Airflow, bootstrap SQL e dados sintéticos.
- `07-12`: Gold em `dbt`, assets Superset, FastAPI, feature store local, treinamento de modelos, scoring batch, drift monitoring e observabilidade base com MLflow/Prometheus/Grafana.

## Estrutura principal

```text
src/
  common/
  ingestion/
  transformation/
  quality/
  api/
  ml/
airflow/
infra/
scripts/
tests/
docs/
```

## Início rápido

```bash
cp .env.example .env
make setup
make sample-data
make features
make lint
make test
```

Para subir a stack local:

```bash
make dev
python -m scripts.setup_minio_buckets
```

Para a stack estendida de consumo e ML:

```bash
make setup-all
make full
make ml
python -m scripts.setup_mlflow
```
# dw-enel-databricks-like
