# Environment Variables

Referência das variáveis de ambiente de `dw-enel-databricks-like`. Gerada a partir de `.env.example` — **não editar seções marcadas como AUTO-GENERATED**.

Copie `.env.example` para `.env` e ajuste conforme o ambiente:

```bash
cp .env.example .env
```

## Core / Logging

<!-- AUTO-GENERATED:ENV-CORE -->
| Variável | Obrigatória | Descrição | Default / Exemplo |
|----------|-------------|-----------|-------------------|
| `ENEL_ENVIRONMENT` | Sim | Perfil do runtime | `dev`, `staging`, `prod` |
| `ENEL_LOG_LEVEL` | Não | Verbosidade de log `structlog` | `INFO` (também `DEBUG`, `WARNING`, `ERROR`) |
| `ENEL_LOG_JSON` | Não | Emite logs estruturados em JSON | `false` |
| `ENEL_PROJECT_ROOT` | Não | Raiz usada para paths relativos | `.` |
<!-- /AUTO-GENERATED:ENV-CORE -->

## MinIO / Object Storage

<!-- AUTO-GENERATED:ENV-MINIO -->
| Variável | Obrigatória | Descrição | Default |
|----------|-------------|-----------|---------|
| `ENEL_MINIO_ENDPOINT` | Sim | Host:porta do MinIO | `localhost:9000` |
| `ENEL_MINIO_ACCESS_KEY` | Sim | Access key | `minio` |
| `ENEL_MINIO_SECRET_KEY` | Sim | Secret key | `minio123` |
| `ENEL_MINIO_SECURE` | Não | Usar TLS | `false` |
| `ENEL_MINIO_BUCKET_LAKEHOUSE` | Sim | Bucket do lakehouse Iceberg | `lakehouse` |
| `ENEL_MINIO_BUCKET_ML_ARTIFACTS` | Sim | Bucket de artefatos ML | `ml-artifacts` |
| `ENEL_MINIO_BUCKET_AIRFLOW_LOGS` | Sim | Bucket de logs Airflow | `airflow-logs` |
| `ENEL_MINIO_BUCKET_EXPORTS` | Sim | Bucket de exports da API | `exports` |
<!-- /AUTO-GENERATED:ENV-MINIO -->

## PostgreSQL (metastore / Airflow)

<!-- AUTO-GENERATED:ENV-POSTGRES -->
| Variável | Obrigatória | Descrição | Default |
|----------|-------------|-----------|---------|
| `ENEL_POSTGRES_HOST` | Sim | Host do Postgres | `localhost` |
| `ENEL_POSTGRES_PORT` | Sim | Porta | `5432` |
| `ENEL_POSTGRES_USER` | Sim | Usuário | `enel` |
| `ENEL_POSTGRES_PASSWORD` | Sim | Senha | `enel123` |
| `ENEL_POSTGRES_DATABASE` | Sim | Banco | `postgres` |
<!-- /AUTO-GENERATED:ENV-POSTGRES -->

## Nessie / Trino

<!-- AUTO-GENERATED:ENV-CATALOG -->
| Variável | Obrigatória | Descrição | Default |
|----------|-------------|-----------|---------|
| `ENEL_NESSIE_URI` | Sim | Endpoint do catálogo Nessie | `http://localhost:19120/api/v2` |
| `ENEL_NESSIE_REF` | Não | Branch Nessie padrão | `main` |
| `ENEL_TRINO_HOST` | Sim | Host do coordenador Trino | `localhost` |
| `ENEL_TRINO_PORT` | Sim | Porta Trino | `8443` |
| `ENEL_TRINO_CATALOG` | Sim | Catálogo Iceberg | `iceberg` |
| `ENEL_TRINO_SCHEMA` | Sim | Schema default | `bronze` |
<!-- /AUTO-GENERATED:ENV-CATALOG -->

## Spark (local mode)

<!-- AUTO-GENERATED:ENV-SPARK -->
| Variável | Obrigatória | Descrição | Default |
|----------|-------------|-----------|---------|
| `ENEL_SPARK_MASTER` | Sim | Master URL | `local[4]` |
| `ENEL_SPARK_DRIVER_MEMORY` | Sim | Memória do driver | `4g` |
| `ENEL_SPARK_SHUFFLE_PARTITIONS` | Sim | `spark.sql.shuffle.partitions` | `8` |
| `ENEL_SPARK_DEFAULT_PARALLELISM` | Sim | `spark.default.parallelism` | `8` |
<!-- /AUTO-GENERATED:ENV-SPARK -->

> **Nota:** valores acima são otimizados para notebook i7-1185G7 / 16GB. Não aumentar sem revisar `docs/architecture/03-hardware-sizing.md`.

## Paths de dados locais

<!-- AUTO-GENERATED:ENV-DATA-PATHS -->
| Variável | Obrigatória | Descrição | Default |
|----------|-------------|-----------|---------|
| `ENEL_DATA_RAW_DIR` | Não | Dados brutos locais | `data/raw` |
| `ENEL_DATA_SAMPLE_DIR` | Não | Dados sintéticos | `data/sample` |
| `ENEL_DATA_FEATURE_STORE_DIR` | Não | Feature store local | `data/feature_store` |
| `ENEL_DATA_MODEL_REGISTRY_DIR` | Não | Registro local de modelos | `data/model_registry` |
| `ENEL_DATA_SCORES_DIR` | Não | Scores batch Gold | `data/gold/scores` |
| `ENEL_DATA_MONITORING_DIR` | Não | Artefatos de drift/monitoria | `data/monitoring` |
| `ENEL_AUDIT_NAMESPACE` | Não | Namespace Nessie de auditoria | `nessie.audit` |
<!-- /AUTO-GENERATED:ENV-DATA-PATHS -->

## MLflow

<!-- AUTO-GENERATED:ENV-MLFLOW -->
| Variável | Obrigatória | Descrição | Default |
|----------|-------------|-----------|---------|
| `ENEL_MLFLOW_TRACKING_URI` | Sim | URI do tracking server | `http://localhost:5000` |
| `ENEL_MLFLOW_TRACKING_ENABLED` | Não | Habilita logging MLflow | `false` |
| `ENEL_ML_USE_NATIVE_BOOSTERS` | Não | Usa boosters nativos LightGBM/XGBoost em vez de sklearn wrapper | `false` |
<!-- /AUTO-GENERATED:ENV-MLFLOW -->

## Airflow / Auth

<!-- AUTO-GENERATED:ENV-AIRFLOW -->
| Variável | Obrigatória | Descrição | Default |
|----------|-------------|-----------|---------|
| `AIRFLOW_FERNET_KEY` | **Sim (prod)** | Chave Fernet para criptografar connections — gerar com `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | `replace-me` |
| `AIRFLOW_ADMIN_USERNAME` | Sim | Usuário admin Airflow | `admin` |
| `AIRFLOW_ADMIN_PASSWORD` | **Sim (prod)** | Senha admin Airflow | `admin` |
| `ENEL_SECRET_KEY` | **Sim (prod)** | Chave de assinatura JWT da FastAPI | `replace-me` |
<!-- /AUTO-GENERATED:ENV-AIRFLOW -->

> **Segurança:** Qualquer valor `replace-me` **deve** ser trocado antes de subir em staging ou prod. Nunca commite `.env` (bloqueado por `.gitignore`).
