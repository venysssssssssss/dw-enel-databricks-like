# dw-enel-databricks-like

Lakehouse analítico open source para ENEL, desenhado para substituir capacidades equivalentes ao Databricks em hardware local limitado.

## Escopo implementado

Esta base materializa as sprints `01-06`:

- estrutura do repositório, configurações e tooling;
- infraestrutura local para MinIO, PostgreSQL, Nessie, Trino, Airflow e Data Docs;
- ingestão Bronze com contratos YAML, metadados técnicos e auditoria;
- transformação Silver com regras de negócio centrais, reconciliação e modularização por domínio;
- camada inicial de qualidade com suites declarativas, checkpoints e alertas;
- dados sintéticos e testes unitários de regras críticas.

## Estrutura principal

```text
src/
  common/
  ingestion/
  transformation/
  quality/
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
make lint
make test
```

Para subir a stack local:

```bash
make dev
python -m scripts.setup_minio_buckets
```
# dw-enel-databricks-like
