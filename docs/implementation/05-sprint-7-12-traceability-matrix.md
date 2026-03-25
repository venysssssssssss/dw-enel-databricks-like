# Matriz de Rastreabilidade — Sprints 07 a 12

Legenda de status:

- `DONE`: implementado no repositório com evidência local.
- `PARTIAL`: parcialmente implementado; ainda falta validação operacional ou cobertura completa.
- `BLOCKED-EXTERNAL`: depende de credenciais, serviços externos, stakeholders ou dados reais.

## Sprint 07

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-033 | Setup do projeto dbt | `DONE` | [dbt_project.yml](/home/vanys/BIG/dw-enel-databricks-like/dbt/dbt_project.yml), [packages.yml](/home/vanys/BIG/dw-enel-databricks-like/dbt/packages.yml), [profiles.yml.example](/home/vanys/BIG/dw-enel-databricks-like/dbt/profiles.yml.example), [dag_dbt.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_dbt.py) | sintaxe via `compileall` | falta `dbt debug/run/test` contra Trino real |
| US-034 | Dimensões conformadas | `DONE` | [dbt/models/dimensions](/home/vanys/BIG/dw-enel-databricks-like/dbt/models/dimensions), [schema.yml](/home/vanys/BIG/dw-enel-databricks-like/dbt/models/dimensions/schema.yml) | testes dbt declarados | falta materializar no catálogo Gold real |
| US-035 | Fatos de notas e efetividade | `DONE` | [fato_notas_operacionais.sql](/home/vanys/BIG/dw-enel-databricks-like/dbt/models/marts/fato_notas_operacionais.sql), [fato_efetividade.sql](/home/vanys/BIG/dw-enel-databricks-like/dbt/models/marts/fato_efetividade.sql) | testes dbt declarados | falta execução incremental real |
| US-036 | Fatos de entrega, pagamento, metas e não lidos | `DONE` | [dbt/models/marts](/home/vanys/BIG/dw-enel-databricks-like/dbt/models/marts), [schema.yml](/home/vanys/BIG/dw-enel-databricks-like/dbt/models/marts/schema.yml) | validação estática | `fato_nao_lidos` segue placeholder até existir fonte real |
| US-037 | Orquestração dbt no Airflow | `DONE` | [dag_dbt.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_dbt.py) | sintaxe via `compileall` | falta rodar no Airflow com dbt instalado |

## Sprint 08

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-038 | Setup Superset | `PARTIAL` | [docker-compose.full.yml](/home/vanys/BIG/dw-enel-databricks-like/infra/docker-compose.full.yml), [superset_config.py](/home/vanys/BIG/dw-enel-databricks-like/infra/config/superset/superset_config.py) | validação estática | falta inicializar Superset e conexão real com Trino |
| US-039 | Datasets Superset | `DONE` | [overview_operacional.sql](/home/vanys/BIG/dw-enel-databricks-like/infra/config/superset/datasets/overview_operacional.sql), [resumo_metas.sql](/home/vanys/BIG/dw-enel-databricks-like/infra/config/superset/datasets/resumo_metas.sql) | revisão SQL | falta cadastro via UI/API do Superset |
| US-040 | Dashboard Visão Geral Operacional | `PARTIAL` | datasets e config Superset | n/a | layout final do dashboard depende de construção no Superset |
| US-041 | Dashboard Entrega de Faturas | `PARTIAL` | assets SQL base disponíveis | n/a | falta montagem no Superset |
| US-042 | Dashboard Metas e Projeção | `PARTIAL` | datasets Gold e assets SQL | n/a | falta montagem no Superset |
| US-043 | Dashboard Inadimplência | `PARTIAL` | Gold + API/ML prontos para consumo | n/a | falta montagem no Superset |
| US-044 | Saved queries / export templates | `DONE` | [saved_queries.sql](/home/vanys/BIG/dw-enel-databricks-like/infra/config/superset/saved_queries.sql) | revisão SQL | falta importar no Superset real |

## Sprint 09

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-045 | App Factory e infraestrutura FastAPI | `DONE` | [main.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/main.py), [config.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/config.py), [Dockerfile.api](/home/vanys/BIG/dw-enel-databricks-like/infra/dockerfiles/Dockerfile.api) | [test_api_app.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_api_app.py) | falta subir a API no compose real |
| US-046 | Trino async client | `DONE` | [trino_client.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/infrastructure/trino_client.py) | [test_api_app.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_api_app.py) com `InMemoryTrinoClient` | falta validar contra Trino real |
| US-047 | Endpoints de exportação | `DONE` | [exports.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/routers/v1/exports.py), [export_service.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/services/export_service.py) | [test_api_app.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_api_app.py) | falta integração real com MinIO e volumes grandes |
| US-048 | Endpoints de métricas | `DONE` | [metrics.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/routers/v1/metrics.py), [metrics_service.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/services/metrics_service.py) | [test_api_app.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_api_app.py) | consultas ainda usam SQL base/fallback |
| US-049 | JWT e autorização | `DONE` | [jwt.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/auth/jwt.py), [permissions.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/auth/permissions.py) | [test_api_app.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_api_app.py) | usuários ainda seedados em memória |
| US-050 | OpenAPI, rate limit, middleware e health | `DONE` | [main.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/main.py), middlewares em [src/api/middleware](/home/vanys/BIG/dw-enel-databricks-like/src/api/middleware) | [test_api_app.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_api_app.py) | falta smoke real com `uvicorn` |

## Sprint 10

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-051 | Setup MLflow | `PARTIAL` | [docker-compose.ml.yml](/home/vanys/BIG/dw-enel-databricks-like/infra/docker-compose.ml.yml), [setup_mlflow.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/setup_mlflow.py), tracking em [tracking.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/models/tracking.py) | validação estática | falta subir MLflow e criar experiments reais |
| US-052 | Features de atraso | `DONE` | [feat_atraso.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/features/feat_atraso.py), [materialize_features.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/materialize_features.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | falta benchmark com 10k+ e Spark real |
| US-053 | Features de inadimplência | `DONE` | [feat_inadimplencia.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/features/feat_inadimplencia.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | falta calibrar com dados reais e validação de negócio |
| US-054 | Feature store materializada | `DONE` | [feature_store.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/feature_store.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | storage local CSV; falta publicar em catálogo real |
| US-055 | Features de metas e anomalias | `DONE` | [feat_metas.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/features/feat_metas.py), [feat_anomalias.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/features/feat_anomalias.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | falta tuning com dados reais |

## Sprint 11

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-056 | Modelo de atraso | `DONE` | [atraso_model.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/models/atraso_model.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | threshold real depende de dataset produtivo |
| US-057 | Modelo de inadimplência | `DONE` | [inadimplencia_model.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/models/inadimplencia_model.py) | cobertura estrutural + CV temporal implementada | falta validação com volumes e métricas reais |
| US-058 | Modelo de metas | `DONE` | [metas_model.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/models/metas_model.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | falta comparação formal vs modelos individuais em dataset real |
| US-059 | Detector de anomalias | `DONE` | [anomalia_model.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/models/anomalia_model.py) | cobertura estrutural | falta validação com labels/feedback real |
| US-060 | Registro local/MLflow dos modelos | `DONE` | [registry.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/models/registry.py), [train_models.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/train_models.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | registro em MLflow real segue dependente da stack |

## Sprint 12

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-061 | Scoring batch | `DONE` | [batch_scorer.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/scoring/batch_scorer.py), [score_models.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/score_models.py), [dag_ml_scoring.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_ml_scoring.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | falta publicar como tabelas Iceberg reais |
| US-062 | Endpoints de scores | `DONE` | [scores.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/routers/v1/scores.py), [score_service.py](/home/vanys/BIG/dw-enel-databricks-like/src/api/services/score_service.py) | [test_api_app.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_api_app.py) | falta medir latência contra base real |
| US-063 | Monitoramento de drift | `DONE` | [drift_detector.py](/home/vanys/BIG/dw-enel-databricks-like/src/ml/monitoring/drift_detector.py), [check_drift.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/check_drift.py), [dag_ml_monitoring.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_ml_monitoring.py) | [test_ml_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ml_pipeline.py) | falta alerta operacional integrado |
| US-064 | Observabilidade Prometheus/Grafana | `PARTIAL` | [docker-compose.ml.yml](/home/vanys/BIG/dw-enel-databricks-like/infra/docker-compose.ml.yml), [prometheus.yml](/home/vanys/BIG/dw-enel-databricks-like/infra/config/prometheus/prometheus.yml), [datasource.yml](/home/vanys/BIG/dw-enel-databricks-like/infra/config/grafana/provisioning/datasources/datasource.yml) | validação estática | falta subir stack e validar dashboards/targets |
| US-065 | DAGs de ML fim a fim | `DONE` | [dag_ml_features.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_ml_features.py), [dag_ml_training.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_ml_training.py), [dag_ml_scoring.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_ml_scoring.py), [dag_ml_monitoring.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_ml_monitoring.py) | sintaxe via `compileall` | falta execução no Airflow real |

## Resumo executivo

| Sprint | Done | Partial | Blocked-External |
|---|---:|---:|---:|
| 07 | 5 | 0 | 0 |
| 08 | 2 | 5 | 0 |
| 09 | 6 | 0 | 0 |
| 10 | 4 | 1 | 0 |
| 11 | 5 | 0 | 0 |
| 12 | 4 | 1 | 0 |

Conclusão:

- o repositório agora cobre localmente a espinha dorsal técnica das sprints `7-12`;
- o que segue `PARTIAL` está concentrado em produtos que exigem instância viva e configuração operacional (`Superset`, `MLflow`, `Prometheus`, `Grafana`);
- o core de código para `API`, `feature store`, `training`, `scoring` e `drift` já possui evidência local com testes unitários;
- a etapa seguinte para converter os `PARTIAL` em `DONE` é subir a stack Docker completa e executar smoke tests end-to-end.
