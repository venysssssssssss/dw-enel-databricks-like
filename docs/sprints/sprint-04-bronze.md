# Sprint 04 — Bronze Layer: Ingestão de Fontes Prioritárias

**Fase**: 2 — Ingestão & Silver
**Duração**: 2 semanas
**Objetivo**: Implementar ingestão real para todas as fontes prioritárias na camada Bronze, com DAGs Airflow, validação de qualidade e metadados completos.

**Pré-requisito**: Sprint 03 completa (Spark, Trino, Airflow, classes base operacionais)

---

## Backlog da Sprint

### US-016: Ingestor — Notas Operacionais
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ingestion/sources/notas_operacionais.py`**:
   ```python
   class NotasOperacionaisIngestor(IncrementalIngestor):
       """Ingestão de notas operacionais — carga incremental por data_alteracao."""

       def extract(self) -> DataFrame:
           df = super().extract()

           # Validações na entrada
           assert df.columns  # não vazio
           self.logger.info(
               "extracted",
               rows=df.count(),
               columns=len(df.columns),
               source=self.config["source"]["name"],
           )
           return df

       def post_extract_validation(self, df: DataFrame) -> None:
           """Validações específicas pós-extração."""
           # Verifica colunas obrigatórias
           required = ["cod_nota", "cod_uc", "data_criacao", "status", "data_alteracao"]
           missing = [c for c in required if c not in df.columns]
           if missing:
               raise ValueError(f"Colunas faltando na fonte: {missing}")
   ```

2. **Criar/validar YAML** `src/ingestion/config/notas_operacionais.yml` com schema real
3. **Criar tabela Iceberg Bronze**:
   ```sql
   CREATE TABLE nessie.bronze.notas_operacionais (
       -- Todas as colunas como STRING (tipagem na Silver)
       cod_nota STRING,
       cod_uc STRING,
       cod_instalacao STRING,
       cod_distribuidora STRING,
       cod_ut STRING,
       cod_co STRING,
       cod_base STRING,
       cod_lote STRING,
       tipo_servico STRING,
       data_criacao STRING,
       data_prevista STRING,
       data_execucao STRING,
       data_alteracao STRING,
       status STRING,
       cod_colaborador STRING,
       latitude STRING,
       longitude STRING,
       -- Metadados técnicos
       _run_id STRING,
       _ingested_at TIMESTAMP,
       _source_file STRING,
       _source_hash STRING,
       _partition_date DATE
   )
   USING iceberg
   PARTITIONED BY (_partition_date)
   ```

**Critério de aceite**:
- Ingestão de CSV de notas com 10k+ registros em < 30 segundos
- Metadados técnicos presentes em todos os registros
- Dados legíveis via Trino: `SELECT * FROM iceberg.bronze.notas_operacionais LIMIT 10`
- Carga incremental funcional (segunda execução traz apenas novos registros)

---

### US-017: Ingestor — Entregas de Fatura
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Criar `src/ingestion/sources/entregas_fatura.py`**:
   ```python
   class EntregasFaturaIngestor(IncrementalIngestor):
       """Ingestão de entregas de fatura — incremental por data_registro."""
       ...
   ```
2. Criar YAML de configuração
3. Criar tabela Iceberg Bronze
4. Testes com dados de amostra

**Critério de aceite**:
- Ingestão funcional com dados de amostra
- Coordenadas GPS (lat/lon) preservadas como STRING no Bronze

---

### US-018: Ingestor — Pagamentos
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Criar `src/ingestion/sources/pagamentos.py`**:
   ```python
   class PagamentosIngestor(IncrementalIngestor):
       """Ingestão de pagamentos — incremental por data_processamento."""
       ...
   ```
2. Criar YAML e tabela Iceberg
3. Tratar valores monetários (vírgula vs ponto decimal)

**Critério de aceite**:
- Valores monetários preservados exatamente como na fonte
- `data_pagamento` pode ser nula (fatura em aberto)

---

### US-019: Ingestor — Cadastros (Snapshot)
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/ingestion/snapshot_ingestor.py`**:
   ```python
   class SnapshotIngestor(BaseIngestor):
       """Ingestor para fontes cadastrais — substitui partição inteira."""

       def _write_bronze(self, df: DataFrame) -> None:
           table_name = f"nessie.bronze.{self.config['source']['name']}"
           # Overwrite da partição do dia
           df.writeTo(table_name).using("iceberg").overwritePartitions()
   ```

2. **Criar ingestores para cada cadastro**:
   - `src/ingestion/sources/cadastro_distribuidoras.py`
   - `src/ingestion/sources/cadastro_uts.py`
   - `src/ingestion/sources/cadastro_cos.py`
   - `src/ingestion/sources/cadastro_bases.py`
   - `src/ingestion/sources/cadastro_ucs.py`
   - `src/ingestion/sources/cadastro_instalacoes.py`
   - `src/ingestion/sources/cadastro_colaboradores.py`

   Cada um herda de `SnapshotIngestor` e implementa validações específicas.

3. Criar YAMLs e tabelas Iceberg para cada cadastro

**Critério de aceite**:
- Todos os 7 cadastros com ingestão funcional
- Re-execução substitui dados (snapshot, não append)
- Relações entre cadastros preservadas (UC pertence a base, base pertence a CO, etc.)

---

### US-020: Ingestor — Metas Operacionais
**Prioridade**: P1
**Story Points**: 3

**Tarefas**:

1. **Criar `src/ingestion/sources/metas_operacionais.py`**:
   ```python
   class MetasIngestor(SnapshotIngestor):
       """Ingestão de metas — snapshot por mês de referência."""

       def _write_bronze(self, df: DataFrame) -> None:
           # Partição por mês de referência, não por data de ingestão
           table_name = f"nessie.bronze.metas_operacionais"
           df = df.withColumn("_partition_date",
               to_date(col("mes_referencia"), "yyyy-MM"))
           df.writeTo(table_name).using("iceberg").overwritePartitions()
   ```

2. YAML e tabela Iceberg

**Critério de aceite**:
- Metas particionadas por mês de referência
- Re-carga do mesmo mês substitui dados anteriores
- Meses diferentes coexistem

---

### US-021: DAG Airflow — Ingestão Diária
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `airflow/dags/dag_ingestion.py`**:
   ```python
   @dag(
       dag_id="ingestion_daily",
       schedule="0 6 * * *",  # 6h diário
       start_date=datetime(2026, 1, 1),
       catchup=False,
       tags=["ingestion", "bronze"],
       max_active_runs=1,
   )
   def ingestion_daily():

       @task_group(group_id="cadastros")
       def ingest_cadastros():
           """Cadastros em paralelo (dentro do limite do executor)."""
           tasks = []
           for source in CADASTRO_SOURCES:
               @task(task_id=f"ingest_{source}")
               def ingest_cadastro(source_name=source):
                   config = load_config(source_name)
                   ingestor = SnapshotIngestor(config, create_spark_session("2g"))
                   result = ingestor.execute()
                   return result.rows_ingested
               tasks.append(ingest_cadastro())
           return tasks

       @task_group(group_id="operacionais")
       def ingest_operacionais():
           """Fontes operacionais (incremental)."""

           @task()
           def ingest_notas():
               config = load_config("notas_operacionais")
               ingestor = NotasOperacionaisIngestor(config, create_spark_session("2g"))
               return ingestor.execute()

           @task()
           def ingest_entregas():
               config = load_config("entregas_fatura")
               ingestor = EntregasFaturaIngestor(config, create_spark_session("2g"))
               return ingestor.execute()

           @task()
           def ingest_pagamentos():
               config = load_config("pagamentos")
               ingestor = PagamentosIngestor(config, create_spark_session("2g"))
               return ingestor.execute()

           return [ingest_notas(), ingest_entregas(), ingest_pagamentos()]

       @task()
       def log_summary(results):
           """Registra resumo da ingestão."""
           ...

       cadastros = ingest_cadastros()
       operacionais = ingest_operacionais()
       log_summary([cadastros, operacionais])

   ingestion_daily()
   ```

2. **Configurar retry e alertas**:
   ```python
   default_args = {
       "retries": 2,
       "retry_delay": timedelta(minutes=5),
       "retry_exponential_backoff": True,
   }
   ```

**Critério de aceite**:
- DAG visível no Airflow UI com task groups organizados
- Execução manual completa sem erros
- Cada task tem logs com `run_id` rastreável
- Retry funciona para falhas transitórias
- Task de resumo reporta contagens por fonte

---

### US-022: Tabela de Auditoria de Ingestão
**Prioridade**: P1
**Story Points**: 3

**Tarefas**:

1. **Criar tabela Iceberg para auditoria**:
   ```sql
   CREATE TABLE nessie.audit.ingestion_log (
       run_id STRING,
       source_name STRING,
       ingestion_type STRING,       -- 'snapshot' | 'incremental'
       rows_ingested BIGINT,
       partition_date DATE,
       watermark_value STRING,      -- último watermark (incrementais)
       duration_seconds DOUBLE,
       status STRING,               -- 'SUCCESS' | 'FAILURE'
       error_message STRING,
       dag_id STRING,
       task_id STRING,
       executed_at TIMESTAMP
   )
   USING iceberg
   PARTITIONED BY (MONTH(executed_at))
   ```

2. **Integrar com BaseIngestor** — método `_audit()` grava nesta tabela
3. **Criar view de monitoramento**:
   ```sql
   -- Últimas ingestões por fonte
   SELECT source_name, MAX(executed_at), SUM(rows_ingested), status
   FROM audit.ingestion_log
   WHERE executed_at >= CURRENT_DATE - INTERVAL '7' DAY
   GROUP BY source_name, status
   ```

**Critério de aceite**:
- Toda ingestão (sucesso ou falha) registrada na tabela de auditoria
- Watermark persistido para cargas incrementais
- View de monitoramento consultável via Trino

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Ingestor Notas Operacionais (incremental) | |
| Ingestor Entregas de Fatura (incremental) | |
| Ingestor Pagamentos (incremental) | |
| 7 Ingestores de Cadastros (snapshot) | |
| Ingestor Metas (snapshot mensal) | |
| DAG Airflow de ingestão diária | |
| Tabela de auditoria de ingestão | |
| 11+ tabelas Bronze criadas no Iceberg | |

## Verificação End-to-End

```bash
# 1. Carregar dados de amostra no diretório de fontes
cp data/sample/*.csv /data/raw/

# 2. Trigger manual da DAG
airflow dags trigger ingestion_daily

# 3. Monitorar no Airflow UI
open http://localhost:8085

# 4. Validar dados via Trino
trino --execute "
  SELECT source_name, rows_ingested, status
  FROM iceberg.audit.ingestion_log
  ORDER BY executed_at DESC
  LIMIT 20
"

# 5. Spot check em cada tabela Bronze
trino --execute "SELECT COUNT(*) FROM iceberg.bronze.notas_operacionais"
trino --execute "SELECT COUNT(*) FROM iceberg.bronze.entregas_fatura"
# ... para cada tabela
```
