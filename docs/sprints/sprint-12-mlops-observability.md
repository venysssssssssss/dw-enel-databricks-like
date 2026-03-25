# Sprint 12 — MLOps, Scoring Pipeline & Observabilidade Final

**Fase**: 4 — ML & Operação Assistida
**Duração**: 2 semanas
**Objetivo**: Fechar o ciclo de ML com scoring batch automatizado, monitoramento de drift, endpoints de scores na API, e observabilidade completa da plataforma com Prometheus + Grafana.

**Pré-requisito**: Sprint 11 completa (Modelos treinados e registrados no MLflow)

---

## Backlog da Sprint

### US-061: Pipeline de Scoring Batch
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **Criar `src/ml/scoring/batch_scorer.py`**:
   ```python
   """Scoring batch para modelos em produção."""

   class BatchScorer:
       def __init__(
           self,
           model_name: str,
           feature_store: FeatureStore,
           mlflow_uri: str,
       ):
           self.model_name = model_name
           self.feature_store = feature_store
           mlflow.set_tracking_uri(mlflow_uri)
           self.logger = get_logger(__name__)

       def score(self, scoring_date: date) -> ScoringResult:
           """Executa scoring completo: load → predict → explain → validate → publish."""
           run_id = str(uuid4())
           start = datetime.now()

           # 1. Carregar modelo Production
           model_uri = f"models:/{self.model_name}/Production"
           model = mlflow.lightgbm.load_model(model_uri)
           model_version = self._get_model_version()

           # 2. Carregar features
           df_features = self.feature_store.load(
               self._get_feature_set_name(),
               scoring_date,
           )
           self.logger.info("features_loaded", rows=len(df_features))

           # 3. Predizer
           feature_cols = self._get_feature_columns(df_features)
           predictions = model.predict(df_features[feature_cols])

           # 4. Calcular SHAP (top 3 por predição)
           explainer = shap.TreeExplainer(model)
           shap_values = explainer.shap_values(df_features[feature_cols])
           explanations = self._extract_top_shap(shap_values, feature_cols, n=3)

           # 5. Montar DataFrame de scores
           df_scores = self._build_score_dataframe(
               df_features, predictions, explanations,
               model_version, run_id, scoring_date,
           )

           # 6. Validar scores
           self._validate_scores(df_scores)

           # 7. Publicar no MinIO (Gold)
           self._publish_scores(df_scores, scoring_date)

           duration = (datetime.now() - start).total_seconds()
           self.logger.info("scoring_completed",
               rows=len(df_scores), duration_s=duration, model=self.model_name)

           return ScoringResult(
               run_id=run_id,
               model_name=self.model_name,
               model_version=model_version,
               rows_scored=len(df_scores),
               scoring_date=scoring_date,
               duration_seconds=duration,
           )

       def _extract_top_shap(self, shap_values, feature_cols, n=3):
           """Extrai top N features por predição com SHAP values."""
           explanations = []
           for i in range(len(shap_values)):
               if isinstance(shap_values, list):
                   vals = shap_values[1][i]  # classe positiva
               else:
                   vals = shap_values[i]

               top_idx = np.argsort(np.abs(vals))[-n:][::-1]
               top_features = [
                   {
                       "feature_name": feature_cols[idx],
                       "shap_value": float(vals[idx]),
                       "direction": "AUMENTA_RISCO" if vals[idx] > 0 else "DIMINUI_RISCO",
                   }
                   for idx in top_idx
               ]
               explanations.append(top_features)
           return explanations

       def _validate_scores(self, df_scores):
           """Validações de sanidade nos scores."""
           # Score entre 0 e 1
           assert df_scores['score'].between(0, 1).all(), "Scores fora do range 0-1"
           # Sem nulos no score
           assert df_scores['score'].notna().all(), "Scores com nulos"
           # Distribuição razoável
           mean_score = df_scores['score'].mean()
           assert 0.01 < mean_score < 0.99, f"Distribuição degenerada: mean={mean_score}"

       def _publish_scores(self, df_scores, scoring_date):
           """Publica scores como tabela Iceberg na Gold."""
           spark_df = self.spark.createDataFrame(df_scores)
           table = f"nessie.gold.score_{self.model_name.replace('-', '_')}"
           spark_df.writeTo(table).using("iceberg") \
               .partitionedBy("data_scoring") \
               .overwritePartitions()
   ```

2. **Implementar scorers para cada modelo**:
   - `AtrasoScorer(BatchScorer)` — score 0-1 + dias estimados
   - `InadimplenciaScorer(BatchScorer)` — probabilidade calibrada + segmentação
   - `MetasScorer(BatchScorer)` — % projetado + flag risco
   - `AnomaliaScorer` — detection score (não herda de BatchScorer)

3. **Criar DAG** (`airflow/dags/dag_ml_scoring.py`):
   ```python
   @dag(
       dag_id="ml_scoring_daily",
       schedule="0 11 * * *",  # 11h, após features
       tags=["ml", "scoring"],
   )
   def ml_scoring():

       @task()
       def score_atraso():
           scorer = AtrasoScorer(feature_store, mlflow_uri)
           return scorer.score(date.today())

       @task()
       def score_inadimplencia():
           scorer = InadimplenciaScorer(feature_store, mlflow_uri)
           return scorer.score(date.today())

       @task()
       def score_metas():
           scorer = MetasScorer(feature_store, mlflow_uri)
           return scorer.score(date.today())

       @task()
       def detect_anomalias():
           detector = AnomaliaScorer(feature_store)
           return detector.detect(date.today())

       @task()
       def validate_all_scores(results):
           """Validação consolidada dos scores."""
           ...

       results = [score_atraso(), score_inadimplencia(), score_metas(), detect_anomalias()]
       validate_all_scores(results)
   ```

**Critério de aceite**:
- 4 scoring pipelines executam diariamente sem erro
- Scores publicados na Gold layer como tabelas Iceberg
- SHAP top 3 presente em cada score
- Validação de sanidade passa
- DAG completa em < 10 minutos

---

### US-062: Endpoints de Scores na FastAPI
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/api/services/score_service.py`**:
   ```python
   class ScoreService:
       def __init__(self, trino: AsyncTrinoClient):
           self.trino = trino

       async def get_scores_atraso(
           self, filters: ScoreFilters, pagination: PaginationParams
       ) -> PaginatedResponse[ScoreAtrasoResponse]:
           query = f"""
               SELECT
                   s.cod_nota, s.score_atraso, s.classe_predita,
                   s.dias_atraso_pred, s.confianca,
                   s.top_feature_1, s.top_feature_1_val,
                   s.top_feature_2, s.top_feature_2_val,
                   s.top_feature_3, s.top_feature_3_val,
                   s.model_version, s.data_scoring,
                   dd.nome_distribuidora, du.nome_ut, dc.nome_co, db.nome_base
               FROM gold.score_atraso_entrega s
               JOIN gold.dim_nota n ON s.cod_nota = n.cod_nota
               ...
               WHERE s.data_scoring = DATE '{filters.data_scoring or "CURRENT_DATE"}'
               {self._build_filters(filters)}
               ORDER BY s.score_atraso DESC
               LIMIT {pagination.page_size}
               OFFSET {(pagination.page - 1) * pagination.page_size}
           """
           results = await self.trino.execute(query)
           return self._to_paginated_response(results, pagination)
   ```

2. **Criar `src/api/routers/v1/scores.py`**:
   - `GET /api/v1/scores/atraso` — listagem com filtros
   - `GET /api/v1/scores/atraso/{cod_nota}` — score individual com explicação
   - `GET /api/v1/scores/inadimplencia` — scores de inadimplência
   - `GET /api/v1/scores/metas` — projeções de meta
   - `GET /api/v1/scores/anomalias` — alertas de anomalia

3. **Testes dos endpoints de scores**

**Critério de aceite**:
- Scores consultáveis via API com filtros e paginação
- Score individual retorna explicação SHAP
- Latência < 2s para consultas paginadas
- Documentação OpenAPI completa

---

### US-063: Monitoramento de Drift
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ml/monitoring/drift_detector.py`**:
   ```python
   """Detecção de drift em features e predições."""

   class DriftDetector:
       def __init__(self, model_name: str, spark: SparkSession):
           self.model_name = model_name
           self.spark = spark
           self.logger = get_logger(__name__)

       def check_feature_drift(
           self, reference_date: date, current_date: date
       ) -> list[DriftResult]:
           """Calcula PSI para cada feature entre datas de referência e atual."""
           ref_features = self._load_features(reference_date)
           cur_features = self._load_features(current_date)

           results = []
           for col in self._get_numeric_features(ref_features):
               psi = self._calculate_psi(ref_features[col], cur_features[col])
               status = (
                   "STABLE" if psi < 0.1 else
                   "MODERATE" if psi < 0.2 else
                   "SIGNIFICANT"
               )
               results.append(DriftResult(
                   feature=col, psi=psi, status=status,
                   reference_date=reference_date, current_date=current_date,
               ))

               if status != "STABLE":
                   self.logger.warning("feature_drift",
                       feature=col, psi=round(psi, 4), status=status)

           return results

       def check_prediction_drift(
           self, reference_date: date, current_date: date
       ) -> DriftResult:
           """Calcula PSI na distribuição dos scores."""
           ref_scores = self._load_scores(reference_date)
           cur_scores = self._load_scores(current_date)
           psi = self._calculate_psi(ref_scores, cur_scores)
           return DriftResult(feature="prediction_score", psi=psi, ...)

       def check_performance(
           self, scoring_date: date
       ) -> PerformanceResult | None:
           """Compara performance real vs baseline (quando labels disponíveis)."""
           # Só possível quando temos labels reais (ex: após execução da nota)
           ...

       @staticmethod
       def _calculate_psi(expected, actual, bins=10):
           """Population Stability Index."""
           breakpoints = np.linspace(
               min(expected.min(), actual.min()),
               max(expected.max(), actual.max()),
               bins + 1,
           )
           expected_pcts = np.histogram(expected, breakpoints)[0] / len(expected)
           actual_pcts = np.histogram(actual, breakpoints)[0] / len(actual)
           expected_pcts = np.clip(expected_pcts, 0.001, None)
           actual_pcts = np.clip(actual_pcts, 0.001, None)
           return float(np.sum(
               (actual_pcts - expected_pcts) * np.log(actual_pcts / expected_pcts)
           ))
   ```

2. **Criar DAG de monitoramento** (`airflow/dags/dag_ml_monitoring.py`):
   ```python
   @dag(
       dag_id="ml_monitoring_daily",
       schedule="0 12 * * *",  # 12h, após scoring
       tags=["ml", "monitoring"],
   )
   def ml_monitoring():

       @task()
       def check_drift_all_models():
           results = {}
           for model in ["atraso", "inadimplencia", "metas"]:
               detector = DriftDetector(model, spark)
               feature_drift = detector.check_feature_drift(
                   reference_date=date.today() - timedelta(days=30),
                   current_date=date.today(),
               )
               prediction_drift = detector.check_prediction_drift(
                   reference_date=date.today() - timedelta(days=30),
                   current_date=date.today(),
               )
               results[model] = {
                   "feature_drift": feature_drift,
                   "prediction_drift": prediction_drift,
               }
           return results

       @task()
       def generate_monitoring_report(drift_results):
           """Gera relatório e persiste."""
           ...

       @task()
       def alert_if_drift(drift_results):
           """Alerta se drift significativo."""
           for model, results in drift_results.items():
               significant = [r for r in results["feature_drift"]
                            if r.status == "SIGNIFICANT"]
               if significant:
                   logger.error("significant_drift_detected",
                       model=model, features=[r.feature for r in significant])

       drift = check_drift_all_models()
       generate_monitoring_report(drift)
       alert_if_drift(drift)
   ```

**Critério de aceite**:
- PSI calculado diariamente para todas as features
- Drift de predição monitorado
- Alertas para PSI > 0.2
- Histórico de drift persistido

---

### US-064: Observabilidade — Prometheus + Grafana
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Adicionar Prometheus e Grafana ao Docker Compose**:
   ```yaml
   prometheus:
     image: prom/prometheus:v2.50.0
     ports:
       - "9090:9090"
     volumes:
       - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
     deploy:
       resources:
         limits:
           memory: 256M

   grafana:
     image: grafana/grafana:11.0.0
     ports:
       - "3000:3000"
     environment:
       GF_SECURITY_ADMIN_PASSWORD: admin
     volumes:
       - grafana_data:/var/lib/grafana
       - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
       - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
     deploy:
       resources:
         limits:
           memory: 256M
   ```

2. **Configurar Prometheus** (`infra/config/prometheus/prometheus.yml`):
   ```yaml
   global:
     scrape_interval: 30s

   scrape_configs:
     - job_name: 'fastapi'
       static_configs:
         - targets: ['api:8000']

     - job_name: 'minio'
       metrics_path: /minio/v2/metrics/cluster
       static_configs:
         - targets: ['minio:9000']

     - job_name: 'trino'
       static_configs:
         - targets: ['trino:8080']
       metrics_path: /v1/info

     - job_name: 'airflow'
       static_configs:
         - targets: ['airflow-webserver:8080']
       metrics_path: /health
   ```

3. **Adicionar métricas à FastAPI**:
   ```python
   from prometheus_fastapi_instrumentator import Instrumentator

   Instrumentator().instrument(app).expose(app)
   # Automaticamente expõe: request count, latency, in_progress
   ```

4. **Criar dashboards Grafana** (provisioned via JSON):

   **Dashboard: Platform Overview**:
   - Uptime de cada serviço
   - Request rate da API (req/s)
   - Latência P50, P95, P99
   - Taxa de erros 5xx
   - MinIO storage utilizado
   - Airflow DAG success rate

   **Dashboard: Data Pipeline**:
   - Última execução de cada DAG
   - Registros ingeridos por dia
   - Registros por camada (Bronze, Silver, Gold)
   - Quality check pass rate
   - Reconciliação delta por tabela

   **Dashboard: ML Operations**:
   - Scores gerados por dia
   - Distribuição de scores (histogram)
   - Feature drift PSI por modelo
   - Model performance (quando labels disponíveis)
   - Anomalias detectadas por dia

**Critério de aceite**:
- Prometheus scraping todos os serviços
- 3 dashboards Grafana provisionados
- Métricas da FastAPI expostas (request count, latency)
- Alertas configuráveis no Grafana
- Grafana acessível em `http://localhost:3000`

---

### US-065: Integração Final e Smoke Tests
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar script de smoke test end-to-end** (`scripts/smoke_test.py`):
   ```python
   """Smoke test completo da plataforma."""

   def test_full_pipeline():
       """Testa o pipeline completo: ingestão → silver → gold → api → ml."""

       # 1. Verificar serviços
       assert check_service("minio", 9000)
       assert check_service("trino", 8443)
       assert check_service("airflow", 8085)
       assert check_service("api", 8000)
       assert check_service("mlflow", 5000)
       assert check_service("superset", 8088)
       print("✓ Todos os serviços respondendo")

       # 2. Verificar dados Bronze
       count_bronze = trino_query("SELECT COUNT(*) FROM iceberg.bronze.notas_operacionais")
       assert count_bronze > 0
       print(f"✓ Bronze: {count_bronze} registros")

       # 3. Verificar dados Silver
       count_silver = trino_query("SELECT COUNT(*) FROM iceberg.silver.notas_operacionais")
       assert count_silver > 0
       print(f"✓ Silver: {count_silver} registros")

       # 4. Verificar dados Gold
       count_gold = trino_query("SELECT COUNT(*) FROM iceberg.gold.fato_notas_operacionais")
       assert count_gold > 0
       print(f"✓ Gold: {count_gold} registros")

       # 5. Verificar API
       token = api_login("admin", "admin")
       export = api_post("/api/v1/exports/notas", token, {
           "periodo_inicio": "2026-01-01",
           "periodo_fim": "2026-03-31",
       })
       assert export["status"] == "READY"
       print(f"✓ API Export: {export['row_count']} registros")

       # 6. Verificar scores
       scores = api_get("/api/v1/scores/atraso?page_size=5", token)
       assert len(scores["data"]) > 0
       print(f"✓ Scores: {scores['total']} scores de atraso")

       # 7. Verificar MLflow
       assert check_service("mlflow", 5000)
       print("✓ MLflow respondendo")

       # 8. Verificar Superset
       assert check_service("superset", 8088)
       print("✓ Superset respondendo")

       # 9. Verificar Grafana
       assert check_service("grafana", 3000)
       print("✓ Grafana respondendo")

       print("\n🎉 SMOKE TEST PASSED — Plataforma operacional!")
   ```

2. **Criar `Makefile` completo** com todos os comandos:
   ```makefile
   # Profiles
   dev:
       docker compose -f infra/docker-compose.dev.yml up -d

   full:
       docker compose -f infra/docker-compose.full.yml up -d

   down:
       docker compose -f infra/docker-compose.dev.yml down

   # Pipeline
   ingest:
       docker compose exec airflow-webserver airflow dags trigger ingestion_daily

   transform:
       docker compose exec airflow-webserver airflow dags trigger transformation_silver_daily

   dbt:
       docker compose exec airflow-webserver airflow dags trigger dbt_gold_daily

   quality:
       docker compose exec airflow-webserver airflow dags trigger data_quality_daily

   ml-features:
       docker compose exec airflow-webserver airflow dags trigger ml_feature_engineering_daily

   ml-score:
       docker compose exec airflow-webserver airflow dags trigger ml_scoring_daily

   # Full pipeline
   pipeline: ingest transform quality dbt ml-features ml-score

   # Tests
   test:
       pytest tests/ -v

   smoke:
       python scripts/smoke_test.py

   # Utilities
   trino-cli:
       docker compose exec trino trino --catalog iceberg --schema gold
   ```

**Critério de aceite**:
- Smoke test passa em ambiente limpo
- Makefile com todos os comandos do ciclo de vida
- Pipeline completo (ingest → score) executa em < 30 minutos
- Todos os serviços dentro dos limites de memória

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Pipeline de scoring batch para 4 modelos | |
| Endpoints de scores na FastAPI | |
| Monitoramento de drift (PSI) | |
| DAG de scoring e monitoramento | |
| Prometheus + Grafana com 3 dashboards | |
| Métricas FastAPI expostas | |
| Script de smoke test end-to-end | |
| Makefile completo | |
| Documentação final atualizada | |

## Verificação Final (Acceptance Criteria da Plataforma)

```
PLATAFORMA COMPLETA — CHECKLIST
================================

[  ] Ingestão Bronze: 11+ tabelas ingeridas diariamente
[  ] Silver Layer: tipagem, classificação ACF/ASF, cálculo de atraso
[  ] Gold Layer: 10 dimensões + 7 tabelas fato (dbt)
[  ] Data Quality: GE checkpoints + reconciliação entre camadas
[  ] Superset: 4 dashboards operacionais com filtros
[  ] FastAPI: 5 endpoints de export + 5 endpoints de scores
[  ] ML Models: 4 modelos treinados e registrados no MLflow
[  ] Scoring: batch diário publicando na Gold
[  ] Drift: monitoramento diário de features e predições
[  ] Observabilidade: Prometheus + Grafana com 3 dashboards
[  ] Orquestração: 7 DAGs Airflow cobrindo todo o ciclo
[  ] Testes: unitários + integração + smoke test
[  ] Documentação: arquitetura, regras, sprints, API (OpenAPI)

HARDWARE: Tudo rodando em 16GB RAM com Docker profiles
```
