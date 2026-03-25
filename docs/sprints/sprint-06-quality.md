# Sprint 06 — Data Quality & Reconciliação

**Fase**: 2 — Ingestão & Silver
**Duração**: 2 semanas
**Objetivo**: Implementar Great Expectations em todas as camadas, criar pipeline de reconciliação automatizada e tabela de auditoria de qualidade.

**Pré-requisito**: Sprint 05 completa (Silver populada)

---

## Backlog da Sprint

### US-029: Great Expectations — Setup e Configuração
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Inicializar projeto Great Expectations**:
   ```bash
   cd src/quality
   great_expectations init
   ```

2. **Configurar datasources** para cada camada:
   ```python
   # Datasource Trino (lê Bronze, Silver e Gold via SQL)
   datasource = context.sources.add_sql(
       name="trino_lakehouse",
       connection_string="trino://enel@localhost:8443/iceberg",
   )
   ```

3. **Criar suites de expectations por tabela**:

   **Bronze — Notas Operacionais**:
   ```python
   suite_bronze_notas = context.add_expectation_suite("bronze_notas_operacionais")
   expectations = [
       # Colunas obrigatórias existem
       ExpectTableColumnsToMatchSet(column_set=[
           "cod_nota", "cod_uc", "data_criacao", "status", "_run_id", "_ingested_at"
       ], exact_match=False),

       # Metadados técnicos não nulos
       ExpectColumnValuesToNotBeNull(column="_run_id"),
       ExpectColumnValuesToNotBeNull(column="_ingested_at"),

       # Volume mínimo
       ExpectTableRowCountToBeGreaterThan(value=100),
   ]
   ```

   **Silver — Notas Operacionais**:
   ```python
   suite_silver_notas = context.add_expectation_suite("silver_notas_operacionais")
   expectations = [
       # Tipos corretos (valores não-nulos onde obrigatório)
       ExpectColumnValuesToNotBeNull(column="cod_nota"),
       ExpectColumnValuesToNotBeNull(column="cod_uc"),
       ExpectColumnValuesToNotBeNull(column="data_criacao"),
       ExpectColumnValuesToNotBeNull(column="status"),
       ExpectColumnValuesToNotBeNull(column="classificacao_acf_asf"),
       ExpectColumnValuesToNotBeNull(column="status_atraso"),

       # Domínios válidos
       ExpectColumnValuesToBeInSet(
           column="classificacao_acf_asf",
           value_set=["ACF_A", "ACF_B", "ACF_C", "ASF_RISCO", "ASF_FORA_RISCO"]
       ),
       ExpectColumnValuesToBeInSet(
           column="status_atraso",
           value_set=["NO_PRAZO", "ATRASADO", "PENDENTE_NO_PRAZO", "PENDENTE_FORA_PRAZO"]
       ),
       ExpectColumnValuesToBeInSet(
           column="status",
           value_set=["CRIADA", "ATRIBUIDA", "EM_CAMPO", "EXECUTADA",
                      "FECHADA", "DEVOLVIDA", "CANCELADA", "REABERTA"]
       ),

       # Unicidade
       ExpectCompoundColumnsToBeUnique(column_list=["cod_nota"]),

       # Datas coerentes
       ExpectColumnPairValuesAToBeGreaterThanB(
           column_A="data_prevista", column_B="data_criacao", or_equal=True,
           mostly=0.95  # 95% — algumas notas podem ter inconsistência
       ),

       # Dias de atraso >= 0
       ExpectColumnValuesToBeBetween(
           column="dias_atraso", min_value=0, max_value=365
       ),

       # Nulidade controlada
       ExpectColumnValuesToNotBeNull(column="cod_distribuidora"),
       ExpectColumnValuesToNotBeNull(column="cod_ut"),
       ExpectColumnValuesToNotBeNull(column="cod_co"),
       ExpectColumnValuesToNotBeNull(column="cod_base"),
   ]
   ```

   **Silver — Pagamentos**:
   ```python
   suite_silver_pagamentos = [
       ExpectColumnValuesToNotBeNull(column="cod_fatura"),
       ExpectColumnValuesToNotBeNull(column="valor_fatura"),
       ExpectColumnValuesToBeBetween(column="valor_fatura", min_value=0.01),
       ExpectColumnValuesToBeOfType(column="valor_fatura", type_="DECIMAL"),
   ]
   ```

   **Silver — Entregas**:
   ```python
   suite_silver_entregas = [
       ExpectColumnValuesToBeBetween(column="latitude", min_value=-35, max_value=6),
       ExpectColumnValuesToBeBetween(column="longitude", min_value=-75, max_value=-30),
       ExpectColumnValuesToBeBetween(column="distancia_metros", min_value=0, max_value=50000),
   ]
   ```

**Critério de aceite**:
- Suites criadas para Bronze e Silver de todas as fontes prioritárias
- Expectations executáveis via checkpoint
- Resultados salvos em Data Docs (HTML estático)

---

### US-030: Pipeline de Reconciliação entre Camadas
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/quality/reconciliation.py`**:
   ```python
   """Reconciliação automatizada entre camadas."""

   @dataclass
   class ReconciliationResult:
       run_id: str
       layer_pair: str         # 'bronze_to_silver' | 'silver_to_gold'
       table_name: str
       source_count: int
       target_count: int
       delta_count: int
       delta_pct: float
       status: str             # 'OK' | 'WARNING' | 'FAIL'
       threshold_pct: float
       details: dict | None = None

   class LayerReconciler:
       """Reconcilia contagens e métricas entre camadas."""

       def __init__(self, spark: SparkSession, thresholds: dict | None = None):
           self.spark = spark
           self.thresholds = thresholds or {
               "bronze_to_silver": 0.05,  # Silver pode ter até 5% menos (dedup)
               "silver_to_gold": 0.10,    # Gold pode divergir até 10% (agregação)
           }

       def reconcile(
           self,
           source_table: str,
           target_table: str,
           layer_pair: str,
           join_keys: list[str] | None = None,
       ) -> ReconciliationResult:
           """Executa reconciliação de contagem e opcionalmente de valores."""
           source_count = self.spark.table(source_table).count()
           target_count = self.spark.table(target_table).count()
           delta = source_count - target_count
           delta_pct = abs(delta) / max(source_count, 1)
           threshold = self.thresholds[layer_pair]

           status = "OK" if delta_pct <= threshold else (
               "WARNING" if delta_pct <= threshold * 2 else "FAIL"
           )

           result = ReconciliationResult(
               run_id=str(uuid4()),
               layer_pair=layer_pair,
               table_name=target_table.split(".")[-1],
               source_count=source_count,
               target_count=target_count,
               delta_count=delta,
               delta_pct=round(delta_pct * 100, 2),
               status=status,
               threshold_pct=threshold * 100,
           )

           self._persist_result(result)
           return result

       def _persist_result(self, result: ReconciliationResult) -> None:
           """Grava resultado na tabela de auditoria."""
           ...
   ```

2. **Criar tabela de auditoria de reconciliação** (conforme `docs/architecture/04-data-flow.md`)

3. **Integrar com DAGs existentes** — adicionar task de reconciliação após cada transformação

**Critério de aceite**:
- Reconciliação Bronze→Silver para todas as tabelas
- Status OK/WARNING/FAIL com thresholds configuráveis
- Resultados persistidos em tabela de auditoria
- WARNING e FAIL geram log de alerta

---

### US-031: Great Expectations — Checkpoints e Scheduling
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar checkpoints por camada**:
   ```python
   checkpoint_bronze = context.add_checkpoint(
       name="checkpoint_bronze_daily",
       validations=[
           {"batch_request": bronze_notas_batch, "expectation_suite_name": "bronze_notas_operacionais"},
           {"batch_request": bronze_entregas_batch, "expectation_suite_name": "bronze_entregas_fatura"},
           {"batch_request": bronze_pagamentos_batch, "expectation_suite_name": "bronze_pagamentos"},
       ],
   )

   checkpoint_silver = context.add_checkpoint(
       name="checkpoint_silver_daily",
       validations=[
           {"batch_request": silver_notas_batch, "expectation_suite_name": "silver_notas_operacionais"},
           # ... todas as tabelas Silver
       ],
   )
   ```

2. **Criar DAG de qualidade** (`airflow/dags/dag_quality.py`):
   ```python
   @dag(
       dag_id="data_quality_daily",
       schedule="0 8 * * *",  # 8h, após Silver
       tags=["quality"],
   )
   def data_quality():

       @task()
       def run_bronze_checks():
           result = context.run_checkpoint("checkpoint_bronze_daily")
           if not result.success:
               raise AirflowException("Bronze quality checks failed")
           return result.statistics

       @task()
       def run_silver_checks():
           result = context.run_checkpoint("checkpoint_silver_daily")
           if not result.success:
               raise AirflowException("Silver quality checks failed")
           return result.statistics

       @task()
       def run_reconciliation():
           reconciler = LayerReconciler(spark)
           results = []
           for table in RECONCILIATION_TABLES:
               r = reconciler.reconcile(
                   f"nessie.bronze.{table}",
                   f"nessie.silver.{table}",
                   "bronze_to_silver",
               )
               results.append(r)
               if r.status == "FAIL":
                   raise AirflowException(f"Reconciliation FAIL: {table}")
           return results

       @task()
       def generate_quality_report(bronze_stats, silver_stats, recon_results):
           """Gera relatório consolidado de qualidade."""
           ...

       b = run_bronze_checks()
       s = run_silver_checks()
       r = run_reconciliation()
       generate_quality_report(b, s, r)
   ```

3. **Data Docs** — servir HTML estático para consulta:
   ```yaml
   # Adicionar ao docker-compose
   ge-datadocs:
     image: nginx:alpine
     ports:
       - "8095:80"
     volumes:
       - ./src/quality/great_expectations/uncommitted/data_docs/local_site:/usr/share/nginx/html:ro
   ```

**Critério de aceite**:
- Checkpoints executam e reportam pass/fail
- DAG de qualidade executa após Silver
- Data Docs acessíveis em `http://localhost:8095`
- Falha de qualidade bloqueia pipeline (no pipeline sem qualidade)

---

### US-032: Alertas de Qualidade
**Prioridade**: P1
**Story Points**: 3

**Tarefas**:

1. **Criar sistema de alertas** (`src/quality/alerts.py`):
   ```python
   class QualityAlertManager:
       """Gerencia alertas de qualidade de dados."""

       def evaluate_and_alert(self, ge_result, recon_results):
           alerts = []

           # Expectations falhando
           for result in ge_result.results:
               if not result.success:
                   alerts.append(QualityAlert(
                       severity="HIGH" if result.expectation_config.get("critical") else "MEDIUM",
                       table=result.meta.get("table"),
                       expectation=result.expectation_config["expectation_type"],
                       details=result.result,
                   ))

           # Reconciliação com problemas
           for r in recon_results:
               if r.status in ("WARNING", "FAIL"):
                   alerts.append(QualityAlert(
                       severity="HIGH" if r.status == "FAIL" else "MEDIUM",
                       table=r.table_name,
                       expectation="reconciliation",
                       details={"delta_pct": r.delta_pct, "threshold": r.threshold_pct},
                   ))

           # Persistir e logar alertas
           for alert in alerts:
               self.logger.warning("quality_alert", **asdict(alert))

           return alerts
   ```

2. **Persistir alertas em tabela de auditoria**

**Critério de aceite**:
- Alertas gerados para toda expectation que falha
- Alertas gerados para reconciliação WARNING/FAIL
- Alertas logados com structlog
- Histórico de alertas consultável via Trino

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Great Expectations configurado com datasources | |
| Suites de expectations para Bronze (todas as tabelas) | |
| Suites de expectations para Silver (todas as tabelas) | |
| Pipeline de reconciliação Bronze→Silver | |
| DAG Airflow de qualidade diária | |
| Data Docs servidos via nginx | |
| Sistema de alertas de qualidade | |
| Tabela de auditoria de qualidade | |

## Verificação

```bash
# 1. Executar checkpoint Bronze
great_expectations checkpoint run checkpoint_bronze_daily

# 2. Executar checkpoint Silver
great_expectations checkpoint run checkpoint_silver_daily

# 3. Ver Data Docs
open http://localhost:8095

# 4. Verificar alertas
trino --execute "
  SELECT severity, table_name, expectation, created_at
  FROM iceberg.audit.quality_alerts
  WHERE created_at >= CURRENT_DATE
  ORDER BY severity, created_at DESC
"

# 5. Verificar reconciliação
trino --execute "
  SELECT table_name, source_count, target_count, delta_pct, status
  FROM iceberg.audit.reconciliation_log
  WHERE executed_at >= CURRENT_DATE
"
```
