# Sprint 03 — Processing & Orchestration

**Fase**: 1 — Fundação
**Duração**: 2 semanas
**Objetivo**: Completar o foundation stack adicionando Trino (query engine), Airflow (orquestração) e validar o pipeline end-to-end com dados de teste.

**Pré-requisito**: Sprint 02 completa (MinIO, PostgreSQL, Nessie, Spark operacionais)

---

## Backlog da Sprint

### US-011: Trino — Setup e Configuração
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Adicionar Trino ao Docker Compose**:
   ```yaml
   trino:
     image: trinodb/trino:440
     ports:
       - "8443:8080"
     volumes:
       - ./config/trino/catalog/iceberg.properties:/etc/trino/catalog/iceberg.properties
       - ./config/trino/config.properties:/etc/trino/config.properties
       - ./config/trino/jvm.config:/etc/trino/jvm.config
     depends_on:
       nessie:
         condition: service_started
       minio:
         condition: service_healthy
     deploy:
       resources:
         limits:
           memory: 2G
   ```

2. **Criar configurações Trino**:

   `infra/config/trino/config.properties`:
   ```properties
   coordinator=true
   node-scheduler.include-coordinator=true
   http-server.http.port=8080
   discovery.uri=http://localhost:8080
   query.max-memory=1GB
   query.max-memory-per-node=1GB
   memory.heap-headroom-per-node=512MB
   ```

   `infra/config/trino/jvm.config`:
   ```
   -server
   -Xmx1536M
   -XX:InitialRAMPercentage=40
   -XX:MaxRAMPercentage=70
   -XX:+UseG1GC
   -XX:G1HeapRegionSize=16M
   -XX:+ExplicitGCInvokesConcurrent
   ```

   `infra/config/trino/catalog/iceberg.properties`:
   ```properties
   connector.name=iceberg
   iceberg.catalog.type=nessie
   iceberg.nessie-catalog.uri=http://nessie:19120/api/v2
   iceberg.nessie-catalog.default-warehouse-dir=s3a://lakehouse/
   iceberg.nessie-catalog.ref=main
   fs.native-s3.enabled=true
   s3.endpoint=http://minio:9000
   s3.path-style-access=true
   s3.region=us-east-1
   s3.aws-access-key=${ENV:MINIO_ACCESS_KEY}
   s3.aws-secret-key=${ENV:MINIO_SECRET_KEY}
   ```

3. **Validar que Trino lê tabelas Iceberg criadas pelo Spark**:
   - Criar tabela via Spark
   - Consultar via Trino (CLI ou Python driver)
   - Validar dados idênticos

**Critério de aceite**:
- Trino responde em `http://localhost:8443`
- Query `SELECT * FROM iceberg.bronze.test` retorna dados
- Trino UI funcional
- Memória dentro do limite (2GB)

---

### US-012: Airflow — Setup e Primeira DAG
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **Criar Dockerfile para Airflow** (`infra/dockerfiles/Dockerfile.airflow`):
   ```dockerfile
   FROM apache/airflow:2.9.3-python3.12

   # Instalar dependências do projeto
   COPY pyproject.toml /opt/airflow/
   RUN pip install --no-cache-dir pyspark pyiceberg trino boto3 structlog

   # Copiar código fonte
   COPY src/ /opt/airflow/src/
   COPY airflow/dags/ /opt/airflow/dags/
   ```

2. **Adicionar Airflow ao Docker Compose**:
   ```yaml
   airflow-webserver:
     build:
       context: ..
       dockerfile: infra/dockerfiles/Dockerfile.airflow
     command: webserver
     environment:
       AIRFLOW__CORE__EXECUTOR: SequentialExecutor
       AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://enel:enel123@postgres:5432/airflow
       AIRFLOW__CORE__FERNET_KEY: ${AIRFLOW_FERNET_KEY}
       AIRFLOW__CORE__LOAD_EXAMPLES: "false"
       AIRFLOW__CORE__PARALLELISM: 4
       AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG: 2
       AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG: 1
       AIRFLOW__WEBSERVER__EXPOSE_CONFIG: "true"
     ports:
       - "8085:8080"
     depends_on:
       postgres:
         condition: service_healthy
     deploy:
       resources:
         limits:
           memory: 1G

   airflow-scheduler:
     build:
       context: ..
       dockerfile: infra/dockerfiles/Dockerfile.airflow
     command: scheduler
     environment:
       <<: *airflow-common-env  # mesmas variáveis
     depends_on:
       airflow-webserver:
         condition: service_started
     deploy:
       resources:
         limits:
           memory: 512M
   ```

3. **Criar DAG de teste** (`airflow/dags/dag_test_pipeline.py`):
   ```python
   """DAG de teste para validar pipeline end-to-end."""
   from airflow.decorators import dag, task
   from datetime import datetime

   @dag(
       dag_id="test_pipeline_e2e",
       schedule=None,  # manual trigger
       start_date=datetime(2026, 1, 1),
       catchup=False,
       tags=["test"],
   )
   def test_pipeline():

       @task()
       def test_minio_connection():
           """Testa conectividade com MinIO."""
           from src.common.minio_client import MinIOClient
           client = MinIOClient(...)
           assert client.file_exists("lakehouse", "")
           return "MinIO OK"

       @task()
       def test_spark_iceberg():
           """Testa Spark + Iceberg + MinIO."""
           from src.common.spark_session import create_spark_session
           spark = create_spark_session(memory="2g")
           spark.sql("SELECT 1 as test").show()
           return "Spark OK"

       @task()
       def test_trino_connection():
           """Testa conectividade com Trino."""
           from trino.dbapi import connect
           conn = connect(host="trino", port=8080, catalog="iceberg")
           cur = conn.cursor()
           cur.execute("SELECT 1")
           assert cur.fetchone()[0] == 1
           return "Trino OK"

       # Execução paralela dos testes
       [test_minio_connection(), test_spark_iceberg(), test_trino_connection()]

   test_pipeline()
   ```

4. **Inicializar Airflow DB**:
   ```bash
   docker compose exec airflow-webserver airflow db migrate
   docker compose exec airflow-webserver airflow users create \
       --username admin --password admin --role Admin \
       --firstname Admin --lastname User --email admin@enel.local
   ```

**Critério de aceite**:
- Airflow UI acessível em `http://localhost:8085`
- DAG `test_pipeline_e2e` visível e executável
- Todos os 3 tasks passam (MinIO, Spark, Trino)
- SequentialExecutor funcional com limites de memória

---

### US-013: Classe Base de Ingestão
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **Criar `src/ingestion/base.py`** — Abstract Base Class para ingestores:

   ```python
   """Classe base para ingestão de dados na camada Bronze."""
   from abc import ABC, abstractmethod
   from dataclasses import dataclass
   from uuid import uuid4
   from datetime import datetime

   @dataclass(frozen=True)
   class IngestionResult:
       run_id: str
       source_name: str
       rows_ingested: int
       partition_date: str
       duration_seconds: float
       status: str  # 'SUCCESS' | 'FAILURE'
       error_message: str | None = None

   class BaseIngestor(ABC):
       """
       Base para todos os ingestores.

       Responsabilidades:
       - Gerar run_id único
       - Adicionar metadados técnicos (_run_id, _ingested_at, _source_hash)
       - Escrever na camada Bronze (MinIO/Iceberg)
       - Registrar resultado no log de auditoria
       """

       def __init__(self, source_config: dict, spark: SparkSession):
           self.config = source_config
           self.spark = spark
           self.run_id = str(uuid4())
           self.logger = get_logger(self.__class__.__name__)

       def execute(self) -> IngestionResult:
           """Template method: extract → enrich → write → audit."""
           start = datetime.now()
           try:
               df = self.extract()
               df_enriched = self._add_technical_metadata(df)
               self._write_bronze(df_enriched)
               self._audit(df_enriched.count(), "SUCCESS")
               return IngestionResult(
                   run_id=self.run_id,
                   source_name=self.config["source"]["name"],
                   rows_ingested=df_enriched.count(),
                   partition_date=str(date.today()),
                   duration_seconds=(datetime.now() - start).total_seconds(),
                   status="SUCCESS",
               )
           except Exception as e:
               self._audit(0, "FAILURE", str(e))
               raise

       @abstractmethod
       def extract(self) -> DataFrame:
           """Extrai dados da fonte. Implementado por cada ingestor."""
           ...

       def _add_technical_metadata(self, df: DataFrame) -> DataFrame:
           """Adiciona colunas técnicas Bronze."""
           return (
               df
               .withColumn("_run_id", lit(self.run_id))
               .withColumn("_ingested_at", current_timestamp())
               .withColumn("_source_file", lit(self.config["source"]["name"]))
               .withColumn("_partition_date", current_date())
           )

       def _write_bronze(self, df: DataFrame) -> None:
           """Escreve na camada Bronze via Iceberg."""
           table_name = f"nessie.bronze.{self.config['source']['name']}"
           df.writeTo(table_name).using("iceberg").createOrReplace()
   ```

2. **Criar `src/ingestion/csv_ingestor.py`**:
   ```python
   class CSVIngestor(BaseIngestor):
       """Ingestor para fontes CSV."""

       def extract(self) -> DataFrame:
           cfg = self.config["source"]
           return (
               self.spark.read
               .option("header", cfg.get("has_header", True))
               .option("delimiter", cfg.get("delimiter", ";"))
               .option("encoding", cfg.get("encoding", "utf-8"))
               .option("inferSchema", "false")  # sempre string, tipagem na Silver
               .csv(cfg["path"])
           )
   ```

3. **Criar `src/ingestion/incremental_ingestor.py`**:
   ```python
   class IncrementalIngestor(CSVIngestor):
       """Ingestor com suporte a watermark para carga incremental."""

       def extract(self) -> DataFrame:
           df_full = super().extract()
           watermark_col = self.config["ingestion"]["watermark_column"]
           last_watermark = self._get_last_watermark()

           if last_watermark:
               df_full = df_full.filter(col(watermark_col) > last_watermark)

           return df_full

       def _get_last_watermark(self) -> str | None:
           """Busca último watermark da tabela de auditoria."""
           ...
   ```

4. **Testes**:
   - Testar `BaseIngestor` com mock de SparkSession
   - Testar `CSVIngestor` com dados de amostra
   - Testar adição de metadados técnicos
   - Testar escrita em Iceberg (integração)

**Critério de aceite**:
- `CSVIngestor` lê CSV e escreve Bronze com metadados
- `IncrementalIngestor` filtra por watermark
- Testes unitários passando
- `run_id` presente em todos os registros

---

### US-014: Classe Base de Transformação Silver
**Prioridade**: P1
**Story Points**: 5

**Tarefas**:

1. **Criar `src/transformation/base.py`**:
   ```python
   """Classe base para transformações Bronze → Silver."""

   class BaseSilverTransformer(ABC):
       """
       Base para transformadores Silver.

       Responsabilidades:
       - Ler da Bronze
       - Aplicar tipagem, normalização, deduplicação
       - Escrever na Silver (Iceberg, merge/append)
       - Registrar reconciliação
       """

       def __init__(self, source_name: str, spark: SparkSession):
           self.source_name = source_name
           self.spark = spark
           self.run_id = str(uuid4())
           self.logger = get_logger(self.__class__.__name__)

       def execute(self) -> TransformationResult:
           """Template method: read_bronze → transform → dedup → write_silver → reconcile."""
           df_bronze = self._read_bronze()
           bronze_count = df_bronze.count()

           df_transformed = self.transform(df_bronze)
           df_deduped = self._deduplicate(df_transformed)

           self._write_silver(df_deduped)
           silver_count = df_deduped.count()

           self._reconcile(bronze_count, silver_count)
           return TransformationResult(...)

       @abstractmethod
       def transform(self, df: DataFrame) -> DataFrame:
           """Transformações específicas por domínio. Implementar nas subclasses."""
           ...

       @abstractmethod
       def get_dedup_keys(self) -> list[str]:
           """Colunas para deduplicação."""
           ...

       @abstractmethod
       def get_dedup_order(self) -> str:
           """Coluna de ordenação para deduplicação (mais recente primeiro)."""
           ...
   ```

2. **Criar `src/transformation/processors/type_caster.py`**:
   ```python
   """Utilitário para cast de tipos baseado em schema YAML."""

   def apply_schema_types(df: DataFrame, schema_config: list[dict]) -> DataFrame:
       """Aplica tipos definidos no YAML de configuração."""
       for col_config in schema_config:
           col_name = col_config["name"]
           target_type = col_config["type"]
           df = df.withColumn(col_name, col(col_name).cast(target_type))
       return df
   ```

3. **Criar `src/transformation/processors/deduplicator.py`**:
   ```python
   """Deduplicação de registros com window function."""

   def deduplicate(
       df: DataFrame,
       keys: list[str],
       order_col: str,
       ascending: bool = False,
   ) -> DataFrame:
       """Remove duplicatas mantendo o registro mais recente."""
       window = Window.partitionBy(*keys).orderBy(
           col(order_col).asc() if ascending else col(order_col).desc()
       )
       return (
           df.withColumn("_row_num", row_number().over(window))
           .filter(col("_row_num") == 1)
           .drop("_row_num")
       )
   ```

**Critério de aceite**:
- Transformer lê Bronze, transforma, deduplica e escreve Silver
- Reconciliação registra contagens Bronze vs Silver
- Type casting funcional para todos os tipos esperados
- Testes unitários passando

---

### US-015: Validação End-to-End com Dados de Teste
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. Carregar dados de amostra da Sprint 01 no MinIO
2. Executar ingestão Bronze via `CSVIngestor`
3. Verificar dados na Bronze via Trino:
   ```sql
   SELECT COUNT(*), MIN(_ingested_at), MAX(_ingested_at)
   FROM iceberg.bronze.notas_operacionais
   ```
4. Executar transformação Silver (stub)
5. Verificar reconciliação
6. Criar DAG Airflow que executa o pipeline completo
7. Trigger manual da DAG e validar sucesso

**Critério de aceite**:
- Pipeline Airflow: ingest → verify → transform → reconcile
- Dados legíveis tanto via Spark quanto via Trino
- Metadados técnicos presentes e corretos
- Zero erros no pipeline
- Logs estruturados com `run_id` rastreável

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Trino operacional com Iceberg connector | |
| Airflow com SequentialExecutor + UI | |
| DAG de teste end-to-end passando | |
| BaseIngestor + CSVIngestor + IncrementalIngestor | |
| BaseSilverTransformer + utilitários | |
| Pipeline end-to-end validado com dados de teste | |

## Riscos da Sprint

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Trino não lê Iceberg via Nessie | Média | Alto | Versões testadas: Trino 440 + Iceberg 1.5 + Nessie 0.80 |
| Airflow consome mais RAM que o esperado | Alta | Médio | SequentialExecutor e limites no Docker |
| Spark JARs conflitam | Média | Alto | Fixar versões exatas em `packages` |
