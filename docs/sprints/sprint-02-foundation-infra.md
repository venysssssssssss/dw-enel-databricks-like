# Sprint 02 — Infraestrutura Core

**Fase**: 1 — Fundação
**Duração**: 2 semanas
**Objetivo**: Subir os serviços base da plataforma via Docker Compose — MinIO, PostgreSQL, Nessie Catalog — e validar conectividade entre eles.

**Pré-requisito**: Sprint 01 completa

---

## Backlog da Sprint

### US-006: Docker Compose — Serviços Base
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **Criar `infra/docker-compose.dev.yml`** com serviços base:

   **MinIO (Object Storage)**:
   ```yaml
   minio:
     image: minio/minio:RELEASE.2024-12-18T13-15-44Z
     command: server /data --console-address ":9001"
     environment:
       MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-minio}
       MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-minio123}
     ports:
       - "9000:9000"   # API S3
       - "9001:9001"   # Console Web
     volumes:
       - minio_data:/data
     deploy:
       resources:
         limits:
           memory: 512M
     healthcheck:
       test: ["CMD", "mc", "ready", "local"]
       interval: 10s
       timeout: 5s
       retries: 5
   ```
   - Configurar com limites de memória (512MB)
   - Volume persistente para dados
   - Healthcheck funcional

   **PostgreSQL (Metastore)**:
   ```yaml
   postgres:
     image: postgres:16-alpine
     environment:
       POSTGRES_USER: ${POSTGRES_USER:-enel}
       POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-enel123}
       POSTGRES_MULTIPLE_DATABASES: airflow,mlflow,superset
     ports:
       - "5432:5432"
     volumes:
       - postgres_data:/var/lib/postgresql/data
       - ./config/postgres/init-multi-db.sh:/docker-entrypoint-initdb.d/init-multi-db.sh
     deploy:
       resources:
         limits:
           memory: 512M
     healthcheck:
       test: ["CMD-SHELL", "pg_isready -U enel"]
       interval: 10s
   ```
   - Script de inicialização para criar múltiplos databases
   - Databases: `airflow`, `mlflow`, `superset`

   **Nessie Catalog**:
   ```yaml
   nessie:
     image: projectnessie/nessie:0.80.0
     environment:
       NESSIE_VERSION_STORE_TYPE: JDBC
       QUARKUS_DATASOURCE_JDBC_URL: jdbc:postgresql://postgres:5432/nessie
       QUARKUS_DATASOURCE_USERNAME: ${POSTGRES_USER:-enel}
       QUARKUS_DATASOURCE_PASSWORD: ${POSTGRES_PASSWORD:-enel123}
     ports:
       - "19120:19120"
     depends_on:
       postgres:
         condition: service_healthy
     deploy:
       resources:
         limits:
           memory: 512M
   ```

2. **Criar script de inicialização de buckets** (`scripts/setup_minio_buckets.py`):
   ```python
   # Buckets a criar:
   buckets = [
       "lakehouse",       # Dados (bronze, silver, gold)
       "ml-artifacts",    # MLflow artifacts
       "airflow-logs",    # Airflow remote logging
       "exports",         # FastAPI export files
   ]
   ```

3. **Criar script `init-multi-db.sh`** para PostgreSQL:
   ```bash
   #!/bin/bash
   set -e
   for db in airflow mlflow superset nessie; do
       psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
           CREATE DATABASE $db;
           GRANT ALL PRIVILEGES ON DATABASE $db TO $POSTGRES_USER;
       EOSQL
   done
   ```

4. **Configurar `.env.example`**:
   ```env
   # MinIO
   MINIO_ACCESS_KEY=minio
   MINIO_SECRET_KEY=minio123

   # PostgreSQL
   POSTGRES_USER=enel
   POSTGRES_PASSWORD=enel123

   # API
   ENEL_SECRET_KEY=your-secret-key-here
   ```

**Critério de aceite**:
- `docker compose -f infra/docker-compose.dev.yml up -d` sobe todos os serviços
- MinIO Console acessível em `http://localhost:9001`
- PostgreSQL aceita conexões em `localhost:5432`
- Nessie API responde em `http://localhost:19120/api/v2`
- Todos os healthchecks passando
- Buckets criados pelo script de setup
- Uso total de RAM < 2GB

---

### US-007: Módulo Comum — SparkSession Factory
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/common/spark_session.py`**:
   ```python
   """Factory para SparkSession configurada para o ambiente local."""

   def create_spark_session(
       app_name: str = "enel-platform",
       memory: str = "4g",
       *,
       iceberg_enabled: bool = True,
   ) -> SparkSession:
       """
       Cria SparkSession otimizada para hardware local (16GB RAM).

       Configurações:
       - Local mode com 4 cores
       - Iceberg + Nessie catalog
       - Shuffle partitions reduzidas (8 ao invés de 200)
       - Adaptive query execution habilitada
       """
   ```

   Configurações Spark obrigatórias:
   ```python
   configs = {
       # Core
       "spark.master": "local[4]",
       "spark.driver.memory": memory,
       "spark.sql.shuffle.partitions": "8",
       "spark.default.parallelism": "8",

       # Adaptive
       "spark.sql.adaptive.enabled": "true",
       "spark.sql.adaptive.coalescePartitions.enabled": "true",
       "spark.sql.adaptive.skewJoin.enabled": "true",

       # Iceberg
       "spark.sql.catalog.nessie": "org.apache.iceberg.spark.SparkCatalog",
       "spark.sql.catalog.nessie.catalog-impl": "org.apache.iceberg.nessie.NessieCatalog",
       "spark.sql.catalog.nessie.uri": f"http://{nessie_host}:19120/api/v2",
       "spark.sql.catalog.nessie.ref": "main",
       "spark.sql.catalog.nessie.warehouse": f"s3a://lakehouse/",
       "spark.sql.catalog.nessie.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",

       # MinIO (S3)
       "spark.hadoop.fs.s3a.endpoint": f"http://{minio_host}:9000",
       "spark.hadoop.fs.s3a.access.key": minio_access_key,
       "spark.hadoop.fs.s3a.secret.key": minio_secret_key,
       "spark.hadoop.fs.s3a.path.style.access": "true",
       "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",

       # Performance
       "spark.sql.parquet.compression.codec": "zstd",
       "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
   }
   ```

2. **Criar testes unitários** (`tests/unit/test_spark_session.py`):
   - Testa criação de sessão
   - Testa configurações aplicadas
   - Testa conectividade com MinIO (mock)

**Critério de aceite**:
- `create_spark_session()` retorna SparkSession funcional
- Leitura/escrita em MinIO via Spark funciona
- Tabelas Iceberg podem ser criadas via Nessie catalog
- Testes unitários passando

---

### US-008: Módulo Comum — MinIO Client
**Prioridade**: P1
**Story Points**: 3

**Tarefas**:

1. **Criar `src/common/minio_client.py`**:
   ```python
   """Cliente MinIO para operações de storage."""
   import boto3
   from botocore.config import Config

   class MinIOClient:
       def __init__(self, endpoint: str, access_key: str, secret_key: str):
           self._client = boto3.client(
               's3',
               endpoint_url=f"http://{endpoint}",
               aws_access_key_id=access_key,
               aws_secret_access_key=secret_key,
               config=Config(signature_version='s3v4'),
           )

       def upload_file(self, local_path: Path, bucket: str, key: str) -> None: ...
       def download_file(self, bucket: str, key: str, local_path: Path) -> None: ...
       def list_objects(self, bucket: str, prefix: str) -> list[str]: ...
       def file_exists(self, bucket: str, key: str) -> bool: ...
       def get_presigned_url(self, bucket: str, key: str, expires: int = 3600) -> str: ...
   ```

2. **Criar testes** contra MinIO real (integration test)

**Critério de aceite**:
- Upload, download, list e presigned URL funcionam
- Integração com MinIO real validada

---

### US-009: Módulo Comum — Logging Estruturado
**Prioridade**: P1
**Story Points**: 2

**Tarefas**:

1. **Criar `src/common/logging.py`**:
   ```python
   """Logging estruturado com structlog."""
   import structlog

   def setup_logging(level: str = "INFO", json_output: bool = False):
       """Configura structlog para toda a aplicação."""
       processors = [
           structlog.contextvars.merge_contextvars,
           structlog.processors.add_log_level,
           structlog.processors.TimeStamper(fmt="iso"),
           structlog.processors.StackInfoRenderer(),
       ]

       if json_output:
           processors.append(structlog.processors.JSONRenderer())
       else:
           processors.append(structlog.dev.ConsoleRenderer())

       structlog.configure(
           processors=processors,
           wrapper_class=structlog.make_filtering_bound_logger(
               getattr(logging, level)
           ),
       )

   def get_logger(name: str) -> structlog.BoundLogger:
       return structlog.get_logger(name)
   ```

2. **Padrão de uso**:
   ```python
   logger = get_logger(__name__)
   logger.info("ingestion_started", source="notas_operacionais", run_id=run_id)
   logger.info("ingestion_completed", rows=15000, duration_s=45.2)
   ```

**Critério de aceite**:
- Logs estruturados em todos os módulos
- Suporta output JSON (produção) e console colorido (dev)
- `run_id` propagado em todos os logs de um pipeline

---

### US-010: Módulo Comum — Configuração Centralizada
**Prioridade**: P1
**Story Points**: 2

**Tarefas**:

1. **Criar `src/common/config.py`**:
   ```python
   """Configuração centralizada via pydantic-settings."""
   from pydantic_settings import BaseSettings, SettingsConfigDict

   class PlatformSettings(BaseSettings):
       model_config = SettingsConfigDict(
           env_file=".env",
           env_prefix="ENEL_",
       )

       # MinIO
       minio_endpoint: str = "localhost:9000"
       minio_access_key: str = "minio"
       minio_secret_key: str = "minio123"
       minio_bucket: str = "lakehouse"

       # PostgreSQL
       postgres_host: str = "localhost"
       postgres_port: int = 5432
       postgres_user: str = "enel"
       postgres_password: str = "enel123"

       # Nessie
       nessie_uri: str = "http://localhost:19120/api/v2"

       # Spark
       spark_driver_memory: str = "4g"
       spark_shuffle_partitions: int = 8

       # Trino
       trino_host: str = "localhost"
       trino_port: int = 8443

   settings = PlatformSettings()
   ```

**Critério de aceite**:
- Todas as configurações lidas de `.env` ou variáveis de ambiente
- Default values funcionais para desenvolvimento local
- Validação de tipos via Pydantic

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Docker Compose com MinIO + PostgreSQL + Nessie | |
| Script de setup de buckets MinIO | |
| SparkSession factory com Iceberg + Nessie + MinIO | |
| MinIO client wrapper | |
| Logging estruturado (structlog) | |
| Configuração centralizada (pydantic-settings) | |
| Testes unitários e de integração | |

## Verificação End-to-End

```bash
# 1. Subir infraestrutura
make dev

# 2. Aguardar healthchecks
docker compose -f infra/docker-compose.dev.yml ps

# 3. Setup MinIO
python scripts/setup_minio_buckets.py

# 4. Testar Spark + Iceberg + MinIO
python -c "
from src.common.spark_session import create_spark_session
spark = create_spark_session()
spark.sql('CREATE NAMESPACE IF NOT EXISTS nessie.bronze')
spark.sql('CREATE TABLE IF NOT EXISTS nessie.bronze.test (id INT, name STRING) USING iceberg')
spark.sql('INSERT INTO nessie.bronze.test VALUES (1, \"test\")')
spark.sql('SELECT * FROM nessie.bronze.test').show()
spark.sql('DROP TABLE nessie.bronze.test')
print('SUCCESS: Spark + Iceberg + MinIO + Nessie working!')
"

# 5. Rodar testes
make test
```

## Riscos da Sprint

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Incompatibilidade Spark ↔ Iceberg ↔ Nessie | Média | Alto | Testar versões específicas antes |
| Docker consuming mais RAM que o esperado | Alta | Médio | Monitorar com `docker stats` e ajustar limites |
| JARs do Iceberg/S3 faltando no Spark | Alta | Alto | Incluir JARs no Dockerfile ou via `packages` |
