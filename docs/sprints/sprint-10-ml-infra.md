# Sprint 10 — Feature Engineering & ML Infrastructure

**Fase**: 4 — ML & Operação Assistida
**Duração**: 2 semanas
**Objetivo**: Configurar MLflow, implementar pipelines de feature engineering para os 4 casos de uso preditivos e criar a feature store materializada.

**Pré-requisito**: Sprint 07 completa (Gold layer com fatos e dimensões)

---

## Backlog da Sprint

### US-051: MLflow — Setup e Configuração
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Adicionar MLflow ao Docker Compose**:
   ```yaml
   mlflow:
     image: ghcr.io/mlflow/mlflow:v2.15.1
     command: >
       mlflow server
       --backend-store-uri postgresql://enel:enel123@postgres:5432/mlflow
       --default-artifact-root s3://ml-artifacts/
       --host 0.0.0.0
       --port 5000
     environment:
       AWS_ACCESS_KEY_ID: ${MINIO_ACCESS_KEY:-minio}
       AWS_SECRET_ACCESS_KEY: ${MINIO_SECRET_KEY:-minio123}
       MLFLOW_S3_ENDPOINT_URL: http://minio:9000
     ports:
       - "5000:5000"
     depends_on:
       postgres:
         condition: service_healthy
       minio:
         condition: service_healthy
     deploy:
       resources:
         limits:
           memory: 384M
   ```

2. **Criar experiments no MLflow**:
   ```python
   import mlflow
   mlflow.set_tracking_uri("http://localhost:5000")

   for experiment in [
       "enel-atraso-entrega",
       "enel-inadimplencia",
       "enel-metas",
       "enel-anomalias",
   ]:
       mlflow.create_experiment(
           experiment,
           artifact_location=f"s3://ml-artifacts/{experiment}",
       )
   ```

3. **Criar script de setup** (`scripts/setup_mlflow.py`)

**Critério de aceite**:
- MLflow UI acessível em `http://localhost:5000`
- 4 experiments criados
- Artifacts salvos no MinIO (bucket `ml-artifacts`)
- Memória dentro do limite (384MB)

---

### US-052: Feature Engineering — Atraso de Entrega
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **Criar `src/ml/features/feat_atraso.py`**:
   ```python
   """Feature engineering para predição de atraso."""

   class AtrasoFeatureBuilder:
       """Constrói features para predição de atraso de entrega."""

       def __init__(self, spark: SparkSession, observation_date: date):
           self.spark = spark
           self.observation_date = observation_date
           self.logger = get_logger(__name__)

       def build(self) -> DataFrame:
           """Pipeline completo de feature engineering."""
           df_notas = self._get_target_notes()

           df = (
               df_notas
               .transform(self._add_note_features)
               .transform(self._add_uc_history_features)
               .transform(self._add_base_features)
               .transform(self._add_collaborator_features)
               .transform(self._add_contextual_features)
               .transform(self._add_target)
           )

           self.logger.info("features_built",
               rows=df.count(),
               features=len(df.columns),
               observation_date=str(self.observation_date))
           return df

       def _get_target_notes(self) -> DataFrame:
           """Obtém notas para scoring (ponto-in-time correto)."""
           return self.spark.sql(f"""
               SELECT *
               FROM nessie.silver.notas_operacionais
               WHERE data_criacao <= DATE '{self.observation_date}'
               AND status NOT IN ('CANCELADA')
           """)

       def _add_note_features(self, df: DataFrame) -> DataFrame:
           """Features da nota individual."""
           return (
               df
               .withColumn("dias_ate_vencimento",
                   datediff(col("data_prevista"), col("data_criacao")))
               .withColumn("dia_semana_criacao",
                   dayofweek(col("data_criacao")))
               .withColumn("dia_semana_previsto",
                   dayofweek(col("data_prevista")))
               .withColumn("flag_fim_de_mes",
                   dayofmonth(col("data_prevista")) >= 25)
               .withColumn("flag_inicio_de_mes",
                   dayofmonth(col("data_prevista")) <= 5)
           )

       def _add_uc_history_features(self, df: DataFrame) -> DataFrame:
           """Features de histórico da UC — point-in-time correct."""
           historico = self.spark.sql(f"""
               SELECT
                   cod_uc,
                   COUNT(*) AS qtd_notas_uc_90d,
                   AVG(CASE WHEN status_atraso IN ('ATRASADO','PENDENTE_FORA_PRAZO')
                       THEN 1.0 ELSE 0.0 END) AS taxa_atraso_uc_90d,
                   AVG(dias_atraso) AS media_dias_atraso_uc,
                   MAX(dias_atraso) AS max_dias_atraso_uc,
                   SUM(CASE WHEN status = 'DEVOLVIDA' THEN 1 ELSE 0 END) AS qtd_devolucoes_uc_90d
               FROM nessie.silver.notas_operacionais
               WHERE data_criacao BETWEEN DATE '{self.observation_date}' - INTERVAL 90 DAY
                   AND DATE '{self.observation_date}'
               AND status NOT IN ('CANCELADA')
               GROUP BY cod_uc
           """)
           return df.join(historico, on="cod_uc", how="left")

       def _add_base_features(self, df: DataFrame) -> DataFrame:
           """Features de desempenho da base — rolling windows."""
           base_stats_7d = self.spark.sql(f"""
               SELECT
                   cod_base,
                   AVG(CASE WHEN status_atraso IN ('ATRASADO','PENDENTE_FORA_PRAZO')
                       THEN 1.0 ELSE 0.0 END) AS taxa_atraso_base_7d,
                   COUNT(*) AS volume_notas_base_7d,
                   AVG(CASE WHEN status IN ('EXECUTADA','FECHADA')
                       THEN 1.0 ELSE 0.0 END) AS efetividade_base_7d
               FROM nessie.silver.notas_operacionais
               WHERE data_criacao BETWEEN DATE '{self.observation_date}' - INTERVAL 7 DAY
                   AND DATE '{self.observation_date}'
               GROUP BY cod_base
           """)

           base_stats_30d = self.spark.sql(f"""
               SELECT
                   cod_base,
                   AVG(CASE WHEN status_atraso IN ('ATRASADO','PENDENTE_FORA_PRAZO')
                       THEN 1.0 ELSE 0.0 END) AS taxa_atraso_base_30d,
                   COUNT(DISTINCT cod_colaborador) AS colaboradores_ativos_30d
               FROM nessie.silver.notas_operacionais
               WHERE data_criacao BETWEEN DATE '{self.observation_date}' - INTERVAL 30 DAY
                   AND DATE '{self.observation_date}'
               GROUP BY cod_base
           """)

           return (
               df
               .join(base_stats_7d, on="cod_base", how="left")
               .join(base_stats_30d, on="cod_base", how="left")
               .withColumn("carga_colaboradores_base",
                   col("volume_notas_base_7d") / greatest(col("colaboradores_ativos_30d"), lit(1)))
           )

       def _add_collaborator_features(self, df: DataFrame) -> DataFrame:
           """Features do colaborador atribuído."""
           colab_stats = self.spark.sql(f"""
               SELECT
                   cod_colaborador,
                   AVG(CASE WHEN status_atraso IN ('ATRASADO','PENDENTE_FORA_PRAZO')
                       THEN 1.0 ELSE 0.0 END) AS taxa_atraso_colaborador_30d,
                   COUNT(*) / 30.0 AS produtividade_colaborador_dia,
                   AVG(CASE WHEN status = 'DEVOLVIDA'
                       THEN 1.0 ELSE 0.0 END) AS taxa_devolucao_colaborador_30d,
                   DATEDIFF(DATE '{self.observation_date}', MIN(data_criacao)) AS experiencia_dias
               FROM nessie.silver.notas_operacionais
               WHERE data_criacao BETWEEN DATE '{self.observation_date}' - INTERVAL 30 DAY
                   AND DATE '{self.observation_date}'
               AND cod_colaborador IS NOT NULL
               GROUP BY cod_colaborador
           """)
           return df.join(colab_stats, on="cod_colaborador", how="left")

       def _add_contextual_features(self, df: DataFrame) -> DataFrame:
           """Features contextuais (metas, tempo)."""
           # TODO: integrar com dim_tempo para feriados
           # TODO: integrar com fato_metas para pressão de meta
           return df

       def _add_target(self, df: DataFrame) -> DataFrame:
           """Adiciona target labels para treinamento."""
           return (
               df
               .withColumn("target_flag_atraso",
                   when(col("status_atraso").isin(["ATRASADO", "PENDENTE_FORA_PRAZO"]),
                       lit(1)).otherwise(lit(0)))
               .withColumn("target_dias_atraso", col("dias_atraso"))
           )
   ```

2. **Testes de feature engineering**:
   - Testar point-in-time correctness (sem data leakage)
   - Testar janelas de 7d, 30d, 90d
   - Testar handling de nulos
   - Testar com dados de amostra

**Critério de aceite**:
- Features geradas para 10k+ notas em < 2 minutos
- Zero data leakage (validado com testes)
- Nulos tratados (fillna ou flag)
- Feature manifest gerado com metadados

---

### US-053: Feature Engineering — Inadimplência
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ml/features/feat_inadimplencia.py`**:
   - Features da fatura (valor, mês, vencimento)
   - Histórico de pagamento da UC (12 meses)
   - Features da UC (classe, consumo, antiguidade)
   - Features regionais (taxa inadimplência da base/CO)
   - Target: `flag_inadimplente` (binário)

2. Seguir mesmo padrão de point-in-time do `feat_atraso.py`

**Critério de aceite**:
- Features de inadimplência geradas corretamente
- Histórico de pagamento com janelas de 3, 6, 12 meses
- `meses_consecutivos_inadimplente` calculado corretamente

---

### US-054: Feature Engineering — Metas
**Prioridade**: P1
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ml/features/feat_metas.py`**:
   - Features de progresso (% decorrido, % realizado, taxa diária)
   - Features históricas (meses anteriores, mesmo mês ano anterior)
   - Features da base (colaboradores ativos, volume pendente)
   - Target: `pct_atingimento_final`, `flag_meta_atingida`

2. **Feature de momentum temporal** — requer granularidade diária ou semanal da fato_metas

**Critério de aceite**:
- Features de momentum calculadas corretamente
- Sazonalidade anual capturada
- Gap de velocidade (taxa atual vs taxa necessária) calculado

---

### US-055: Feature Store — Materialização e DAG
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ml/features/feature_store.py`**:
   ```python
   class FeatureStore:
       """Gerencia materialização e leitura de features."""

       def __init__(self, spark: SparkSession, minio: MinIOClient):
           self.spark = spark
           self.minio = minio
           self.base_path = "s3a://lakehouse/ml/features"

       def materialize(
           self, feature_set: str, df: DataFrame, observation_date: date
       ) -> str:
           """Materializa features no MinIO como tabela Iceberg."""
           table_name = f"nessie.ml_features.{feature_set}"
           partition_date = str(observation_date)

           df_with_meta = (
               df
               .withColumn("_feature_date", lit(partition_date))
               .withColumn("_materialized_at", current_timestamp())
           )

           df_with_meta.writeTo(table_name).using("iceberg") \
               .partitionedBy("_feature_date") \
               .createOrReplace()

           # Gerar manifest
           manifest = self._generate_manifest(feature_set, df, observation_date)
           self._save_manifest(feature_set, manifest)

           return table_name

       def load(self, feature_set: str, observation_date: date) -> DataFrame:
           """Carrega features para uma data específica."""
           return self.spark.sql(f"""
               SELECT * FROM nessie.ml_features.{feature_set}
               WHERE _feature_date = '{observation_date}'
           """)
   ```

2. **Criar DAG** (`airflow/dags/dag_ml_features.py`):
   ```python
   @dag(
       dag_id="ml_feature_engineering_daily",
       schedule="0 10 * * *",  # 10h, após dbt Gold
       tags=["ml", "features"],
   )
   def ml_feature_engineering():

       @task()
       def build_atraso_features():
           builder = AtrasoFeatureBuilder(spark, date.today())
           df = builder.build()
           store = FeatureStore(spark, minio)
           store.materialize("feat_atraso", df, date.today())

       @task()
       def build_inadimplencia_features():
           builder = InadimplenciaFeatureBuilder(spark, date.today())
           df = builder.build()
           store = FeatureStore(spark, minio)
           store.materialize("feat_inadimplencia", df, date.today())

       @task()
       def build_metas_features():
           builder = MetasFeatureBuilder(spark, date.today())
           df = builder.build()
           store = FeatureStore(spark, minio)
           store.materialize("feat_metas", df, date.today())

       @task()
       def validate_features():
           """Great Expectations nos features."""
           ...

       [build_atraso_features(), build_inadimplencia_features(), build_metas_features()] >> validate_features()
   ```

**Critério de aceite**:
- Feature store materializa 3 feature sets diariamente
- Features carregáveis por data via `FeatureStore.load()`
- Manifests gerados com metadados de cada feature set
- DAG Airflow executa sem erros
- Validação de qualidade nos features

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| MLflow operacional com 4 experiments | |
| Feature builder: Atraso de Entrega (~20 features) | |
| Feature builder: Inadimplência (~20 features) | |
| Feature builder: Metas (~15 features) | |
| Feature Store com materialização em Iceberg | |
| DAG Airflow para feature engineering diário | |
| Feature manifests com documentação | |
| Testes de point-in-time correctness | |
