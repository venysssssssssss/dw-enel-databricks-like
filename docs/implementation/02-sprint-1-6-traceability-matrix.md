# Matriz de Rastreabilidade — Sprints 01 a 06

Legenda de status:

- `DONE`: implementado no repositório com evidência local.
- `PARTIAL`: parcialmente implementado; ainda falta validação operacional ou cobertura completa.
- `BLOCKED-EXTERNAL`: depende de stakeholders, dados reais, credenciais ou serviços externos.

## Sprint 01

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-001 | Setup do repositório Git e estrutura | `DONE` | `src/`, `airflow/`, `infra/`, `tests/`, `scripts/`, `dbt/`, [README.md](/home/vanys/BIG/dw-enel-databricks-like/README.md) | sintaxe via `compileall` | branch `main` não foi renomeada por limitação do sandbox |
| US-002 | Ferramentas de desenvolvimento | `DONE` | [pyproject.toml](/home/vanys/BIG/dw-enel-databricks-like/pyproject.toml), [.pre-commit-config.yaml](/home/vanys/BIG/dw-enel-databricks-like/.pre-commit-config.yaml), [Makefile](/home/vanys/BIG/dw-enel-databricks-like/Makefile) | testes unitários preparados | execução real de `make setup` ainda depende de instalar dependências |
| US-003 | Mapeamento de fontes reais | `PARTIAL` | contratos YAML em [src/ingestion/config](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/config) | [test_config_models.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_config_models.py) | falta amostra real, owners e divergências reais |
| US-004 | Validação do glossário operacional | `PARTIAL` | regras materializadas em [business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/processors/business_rules.py) | [test_business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_business_rules.py) | falta aprovação formal com negócio |
| US-005 | Geração de dados de amostra e seed `dim_tempo` | `DONE` | [generate_sample_data.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/generate_sample_data.py), [seed_dim_tempo.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/seed_dim_tempo.py) | [test_sample_data.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_sample_data.py), [test_scripts.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_scripts.py) | executado localmente com `.venv`; falta só validação contra schemas reais |

## Sprint 02

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-006 | Docker Compose serviços base | `PARTIAL` | [infra/docker-compose.yml](/home/vanys/BIG/dw-enel-databricks-like/infra/docker-compose.yml), [infra/docker-compose.dev.yml](/home/vanys/BIG/dw-enel-databricks-like/infra/docker-compose.dev.yml), [init-multi-db.sh](/home/vanys/BIG/dw-enel-databricks-like/infra/config/postgres/init-multi-db.sh) | validação estática | falta subir e validar MinIO/Postgres/Nessie reais |
| US-007 | SparkSession factory | `DONE` | [spark_session.py](/home/vanys/BIG/dw-enel-databricks-like/src/common/spark_session.py) | [test_spark_session.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_spark_session.py) | falta validar com Spark/Iceberg reais |
| US-008 | MinIO client | `DONE` | [minio_client.py](/home/vanys/BIG/dw-enel-databricks-like/src/common/minio_client.py) | [test_minio_client.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_minio_client.py) | falta integração real com MinIO |
| US-009 | Logging estruturado | `DONE` | [logging.py](/home/vanys/BIG/dw-enel-databricks-like/src/common/logging.py) | cobertura indireta nos módulos | falta validar propagação end-to-end com Airflow/Spark |
| US-010 | Configuração centralizada | `DONE` | [config.py](/home/vanys/BIG/dw-enel-databricks-like/src/common/config.py), [.env.example](/home/vanys/BIG/dw-enel-databricks-like/.env.example) | [test_config_models.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_config_models.py) | falta execução real com `.env` carregado |

## Sprint 03

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-011 | Trino setup | `PARTIAL` | configs em [infra/config/trino](/home/vanys/BIG/dw-enel-databricks-like/infra/config/trino) | validação estática | falta subir Trino e consultar Iceberg real |
| US-012 | Airflow setup e DAG inicial | `PARTIAL` | [Dockerfile.airflow](/home/vanys/BIG/dw-enel-databricks-like/infra/dockerfiles/Dockerfile.airflow), [dag_test_pipeline.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_test_pipeline.py) | sintaxe via `compileall` | falta inicializar DB e rodar DAG |
| US-013 | Classe base de ingestão | `DONE` | [base.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/base.py), [csv_ingestor.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/csv_ingestor.py), [incremental_ingestor.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/incremental_ingestor.py) | [test_ingestion_base.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ingestion_base.py) | falta integração real Spark/Iceberg |
| US-014 | Classe base de transformação Silver | `DONE` | [transformation/base.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/base.py), processors em [src/transformation/processors](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/processors) | [test_business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_business_rules.py) | falta validação Spark real |
| US-015 | Validação end-to-end com dados de teste | `PARTIAL` | scripts [run_ingestion.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/run_ingestion.py), [run_transformation.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/run_transformation.py) | placeholders preparados | falta execução real do pipeline |

## Sprint 04

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-016 | Ingestor notas operacionais | `DONE` | [notas_operacionais.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/sources/notas_operacionais.py), [notas_operacionais.yml](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/config/notas_operacionais.yml) | [test_ingestion_base.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_ingestion_base.py) | falta benchmark e carga incremental real |
| US-017 | Ingestor entregas de fatura | `DONE` | [entregas_fatura.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/sources/entregas_fatura.py) | cobertura estrutural | falta integração real |
| US-018 | Ingestor pagamentos | `DONE` | [pagamentos.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/sources/pagamentos.py) | cobertura estrutural | falta integração real |
| US-019 | Ingestores snapshot de cadastros | `DONE` | [snapshot_ingestor.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/snapshot_ingestor.py), [cadastros.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/sources/cadastros.py) | cobertura estrutural | falta integração real |
| US-020 | Ingestor metas operacionais | `DONE` | [metas_operacionais.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/sources/metas_operacionais.py) | cobertura estrutural | falta integração real |
| US-021 | DAG de ingestão diária | `DONE` | [dag_ingestion.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_ingestion.py) | sintaxe via `compileall` | falta executar no Airflow |
| US-022 | Tabela de auditoria de ingestão | `DONE` | [src/ingestion/table_sql.py](/home/vanys/BIG/dw-enel-databricks-like/src/ingestion/table_sql.py), bootstrap em [scripts/bootstrap_sql.py](/home/vanys/BIG/dw-enel-databricks-like/scripts/bootstrap_sql.py), SQL gerado em `/infra/sql` | [test_table_sql.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_table_sql.py), [test_scripts.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_scripts.py) | falta aplicar DDL em ambiente Iceberg real |

## Sprint 05

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-023 | Silver notas operacionais | `DONE` | [notas_operacionais.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/silver/notas_operacionais.py) | [test_business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_business_rules.py) | falta validar com DataFrame Spark real |
| US-024 | Silver entregas de fatura | `DONE` | [entregas_fatura.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/silver/entregas_fatura.py) | [test_business_rules.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_business_rules.py) | falta validar UDF real em Spark |
| US-025 | Silver pagamentos | `DONE` | [pagamentos.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/silver/pagamentos.py) | cobertura estrutural | falta validar em Spark real |
| US-026 | Silver cadastros conformados | `PARTIAL` | [cadastros.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/silver/cadastros.py), [referential.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/processors/referential.py) | cobertura estrutural | falta pipeline completo de checagem referencial entre tabelas |
| US-027 | Silver metas operacionais | `DONE` | [metas_operacionais.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/silver/metas_operacionais.py) | cobertura estrutural | falta validar no Spark real |
| US-028 | DAG de transformação Silver | `DONE` | [dag_transformation.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_transformation.py) | sintaxe via `compileall` | falta execução no Airflow |

## Sprint 06

| ID | Item | Status | Evidência | Testes | Gap |
|---|---|---|---|---|---|
| US-029 | Great Expectations setup e suites | `PARTIAL` | [src/quality/suites.py](/home/vanys/BIG/dw-enel-databricks-like/src/quality/suites.py), [gx_runner.py](/home/vanys/BIG/dw-enel-databricks-like/src/quality/gx_runner.py) | [test_quality_suites.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_quality_suites.py) | falta projeto GE inicializado e checkpoints reais |
| US-030 | Reconciliação entre camadas | `DONE` | [reconciliation.py](/home/vanys/BIG/dw-enel-databricks-like/src/quality/reconciliation.py), [src/transformation/table_sql.py](/home/vanys/BIG/dw-enel-databricks-like/src/transformation/table_sql.py) | [test_reconciliation.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_reconciliation.py) | falta persistência validada em Iceberg real |
| US-031 | Checkpoints e scheduling | `PARTIAL` | [dag_quality.py](/home/vanys/BIG/dw-enel-databricks-like/airflow/dags/dag_quality.py) | sintaxe via `compileall` | falta executar checkpoints reais e Data Docs |
| US-032 | Alertas de qualidade | `DONE` | [alerts.py](/home/vanys/BIG/dw-enel-databricks-like/src/quality/alerts.py) | [test_quality_alerts.py](/home/vanys/BIG/dw-enel-databricks-like/tests/unit/test_quality_alerts.py) | falta tabela Iceberg e logs reais validados |

## Resumo executivo

| Sprint | Done | Partial | Blocked-External |
|---|---:|---:|---:|
| 01 | 3 | 2 | 0 |
| 02 | 4 | 1 | 0 |
| 03 | 2 | 3 | 0 |
| 04 | 7 | 0 | 0 |
| 05 | 5 | 1 | 0 |
| 06 | 2 | 2 | 0 |

Conclusão:

- a base de código cobre a maior parte do escopo técnico local das sprints `1-6`;
- o que ainda impede marcar tudo como `DONE` é majoritariamente execução operacional real, integração com serviços e validação de negócio;
- validação local já executada: `python3 -m compileall src scripts tests airflow`, `pytest tests -q`, `python -m scripts.generate_sample_data --rows 50`, `python -m scripts.seed_dim_tempo --output data/sample/dim_tempo.csv`, `python -m scripts.bootstrap_sql --output-dir infra/sql`;
- a próxima etapa para fechar de fato é subir a stack Docker e executar smoke/integration flows reais;
- `ruff` e `mypy` ainda têm pendências relevantes e não devem ser considerados concluídos nesta entrega.
