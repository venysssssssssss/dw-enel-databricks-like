# Sprint 05 — Silver Layer: Curadoria e Padronização

**Fase**: 2 — Ingestão & Silver
**Duração**: 2 semanas
**Objetivo**: Implementar a camada Silver para todas as fontes prioritárias — tipagem, normalização, deduplicação, classificação ACF/ASF, cálculos de atraso e historização.

**Pré-requisito**: Sprint 04 completa (Bronze populada com dados)

---

## Backlog da Sprint

### US-023: Silver — Notas Operacionais
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **Criar `src/transformation/silver/notas_operacionais.py`**:
   ```python
   class NotasOperacionaisSilverTransformer(BaseSilverTransformer):

       def get_dedup_keys(self) -> list[str]:
           return ["cod_nota"]

       def get_dedup_order(self) -> str:
           return "data_alteracao"

       def transform(self, df: DataFrame) -> DataFrame:
           return (
               df
               .transform(self._apply_types)
               .transform(self._normalize_keys)
               .transform(self._classify_acf_asf)
               .transform(self._calculate_delay)
               .transform(self._add_silver_metadata)
           )

       def _apply_types(self, df: DataFrame) -> DataFrame:
           """Cast de STRING Bronze → tipos corretos."""
           return (
               df
               .withColumn("cod_nota", col("cod_nota").cast("bigint"))
               .withColumn("cod_uc", col("cod_uc").cast("bigint"))
               .withColumn("cod_instalacao", col("cod_instalacao").cast("bigint"))
               .withColumn("cod_distribuidora", col("cod_distribuidora").cast("int"))
               .withColumn("cod_ut", col("cod_ut").cast("int"))
               .withColumn("cod_co", col("cod_co").cast("int"))
               .withColumn("cod_base", col("cod_base").cast("int"))
               .withColumn("cod_lote", col("cod_lote").cast("int"))
               .withColumn("data_criacao", to_date(col("data_criacao"), "dd/MM/yyyy"))
               .withColumn("data_prevista", to_date(col("data_prevista"), "dd/MM/yyyy"))
               .withColumn("data_execucao", to_date(col("data_execucao"), "dd/MM/yyyy"))
               .withColumn("data_alteracao",
                   to_timestamp(col("data_alteracao"), "dd/MM/yyyy HH:mm:ss"))
               .withColumn("latitude", col("latitude").cast("double"))
               .withColumn("longitude", col("longitude").cast("double"))
           )

       def _normalize_keys(self, df: DataFrame) -> DataFrame:
           """Padroniza valores textuais."""
           return (
               df
               .withColumn("tipo_servico", upper(trim(col("tipo_servico"))))
               .withColumn("status", upper(trim(col("status"))))
           )

       def _classify_acf_asf(self, df: DataFrame) -> DataFrame:
           """Aplica classificação ACF/ASF conforme regras de negócio."""
           acf_a_types = ["CORTE", "RELIGACAO", "SUBSTITUICAO_MEDIDOR",
                          "INSTALACAO_MEDIDOR", "REGULARIZACAO_FRAUDE"]
           acf_b_types = ["INSPECAO_PROGRAMADA", "VERIFICACAO_MEDIDOR",
                          "REVISAO_LEITURA"]

           return df.withColumn(
               "classificacao_acf_asf",
               when(col("tipo_servico").isin(acf_a_types), lit("ACF_A"))
               .when(col("tipo_servico").isin(acf_b_types), lit("ACF_B"))
               .when(col("flag_impacto_faturamento") == True, lit("ACF_C"))
               .when(col("flag_risco") == True, lit("ASF_RISCO"))
               .otherwise(lit("ASF_FORA_RISCO"))
           )

       def _calculate_delay(self, df: DataFrame) -> DataFrame:
           """Calcula dias de atraso e status temporal."""
           return (
               df
               .withColumn("dias_atraso",
                   when(
                       col("data_execucao").isNotNull() &
                       (col("data_execucao") > col("data_prevista")),
                       datediff(col("data_execucao"), col("data_prevista"))
                   )
                   .when(
                       col("data_execucao").isNull() &
                       (current_date() > col("data_prevista")),
                       datediff(current_date(), col("data_prevista"))
                   )
                   .otherwise(lit(0))
               )
               .withColumn("status_atraso",
                   when(
                       col("data_execucao").isNotNull() &
                       (col("data_execucao") <= col("data_prevista")),
                       lit("NO_PRAZO")
                   )
                   .when(
                       col("data_execucao").isNotNull() &
                       (col("data_execucao") > col("data_prevista")),
                       lit("ATRASADO")
                   )
                   .when(
                       col("data_execucao").isNull() &
                       (current_date() <= col("data_prevista")),
                       lit("PENDENTE_NO_PRAZO")
                   )
                   .when(
                       col("data_execucao").isNull() &
                       (current_date() > col("data_prevista")),
                       lit("PENDENTE_FORA_PRAZO")
                   )
               )
               .withColumn("flag_risco",
                   col("classificacao_acf_asf").isin(["ASF_RISCO"])
               )
           )
   ```

2. **Criar tabela Iceberg Silver** com schema tipado (conforme `docs/architecture/04-data-flow.md`)
3. **Testes**:
   - Testar cada método de transformação individualmente
   - Testar pipeline completo Bronze → Silver
   - Testar classificação ACF/ASF com cenários de edge case
   - Testar cálculo de atraso: no prazo, atrasado, pendente no prazo, pendente fora

**Critério de aceite**:
- Todos os campos tipados corretamente
- Classificação ACF/ASF aplicada em 100% dos registros
- `dias_atraso` e `status_atraso` calculados corretamente
- Deduplicação por `cod_nota` (mantém mais recente)
- Zero registros com `classificacao_acf_asf` nulo

---

### US-024: Silver — Entregas de Fatura
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/transformation/silver/entregas_fatura.py`**:

   Transformações específicas:
   - Cast lat/lon para DOUBLE
   - Calcular `distancia_metros` via Haversine:
     ```python
     def _calculate_distance(self, df: DataFrame) -> DataFrame:
         """Calcula distância Haversine entre entrega e coordenada da UC."""
         return df.withColumn(
             "distancia_metros",
             haversine_udf(
                 col("lat_entrega"), col("lon_entrega"),
                 col("lat_uc"), col("lon_uc")
             )
         ).withColumn(
             "flag_dentro_coordenada",
             col("distancia_metros") <= lit(100.0)  # 100m tolerância
         )
     ```
   - Calcular `flag_antes_vencimento`:
     ```python
     .withColumn("flag_antes_vencimento",
         datediff(col("data_vencimento"), col("data_entrega")) >= 5
     )
     ```
   - Calcular `dias_para_entrega`: `datediff(data_entrega, data_emissao)`

2. **Criar UDF Haversine**:
   ```python
   @udf(returnType=DoubleType())
   def haversine_udf(lat1, lon1, lat2, lon2):
       """Distância Haversine em metros."""
       from math import radians, cos, sin, asin, sqrt
       R = 6371000  # raio da Terra em metros
       lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
       dlat = lat2 - lat1
       dlon = lon2 - lon1
       a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
       return 2 * R * asin(sqrt(a))
   ```

**Critério de aceite**:
- Distância calculada corretamente (testar com coordenadas conhecidas)
- `flag_dentro_coordenada` e `flag_antes_vencimento` derivados
- Coordenadas nulas tratadas (distância = NULL)

---

### US-025: Silver — Pagamentos
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Criar `src/transformation/silver/pagamentos.py`**:

   Transformações específicas:
   - Cast `valor_fatura` e `valor_pago` para DECIMAL(12,2)
   - Tratar separador decimal (vírgula → ponto se necessário)
   - Calcular `flag_inadimplente`:
     ```python
     .withColumn("flag_inadimplente",
         (col("data_pagamento").isNull()) &
         (datediff(current_date(), col("data_vencimento")) > 30)
     )
     ```
   - Calcular `dias_atraso_pagamento`:
     ```python
     .withColumn("dias_atraso_pagamento",
         when(col("data_pagamento").isNotNull(),
             greatest(datediff(col("data_pagamento"), col("data_vencimento")), lit(0))
         ).otherwise(
             datediff(current_date(), col("data_vencimento"))
         )
     )
     ```

**Critério de aceite**:
- Valores monetários com 2 casas decimais
- `flag_inadimplente` calculado corretamente
- Fatura em aberto (sem pagamento) tratada

---

### US-026: Silver — Cadastros Conformados
**Prioridade**: P1
**Story Points**: 5

**Tarefas**:

1. **Criar transformers para cada cadastro**:
   - `silver/cadastro_distribuidoras.py` — padronizar nomes, UF
   - `silver/cadastro_uts.py` — vincular a distribuidora
   - `silver/cadastro_cos.py` — vincular a UT
   - `silver/cadastro_bases.py` — vincular a CO, classificar base/polo
   - `silver/cadastro_ucs.py` — padronizar classe, tipo ligação
   - `silver/cadastro_instalacoes.py` — padronizar endereço
   - `silver/cadastro_colaboradores.py` — padronizar nome, equipe

2. **Validar integridade referencial**:
   ```python
   def validate_referential_integrity(df_child, df_parent, fk_col, pk_col):
       """Verifica que todas as FKs existem na tabela pai."""
       orphans = df_child.join(df_parent, df_child[fk_col] == df_parent[pk_col], "left_anti")
       orphan_count = orphans.count()
       if orphan_count > 0:
           logger.warning("orphan_records", count=orphan_count, fk=fk_col)
       return orphan_count
   ```

**Critério de aceite**:
- Hierarquia organizacional íntegra: Distribuidora → UT → CO → Base
- UCs vinculadas a bases existentes
- Colaboradores com equipe/função padronizados
- Integridade referencial validada e logada

---

### US-027: Silver — Metas Operacionais
**Prioridade**: P1
**Story Points**: 3

**Tarefas**:

1. **Criar `src/transformation/silver/metas_operacionais.py`**:

   Transformações específicas:
   - Cast `valor_meta` e `valor_realizado` para DOUBLE
   - Calcular `pct_atingimento`: `valor_realizado / valor_meta * 100`
   - Calcular `status_meta`:
     ```python
     .withColumn("status_meta",
         when(col("pct_atingimento") >= 100, lit("ATINGIDA"))
         .when(col("pct_atingimento") >= 90, lit("EM_RISCO"))
         .when(col("pct_atingimento") >= 70, lit("CRITICA"))
         .otherwise(lit("NAO_ATINGIDA"))
     )
     ```
   - Vincular a hierarquia: distribuidora → UT → CO → base

**Critério de aceite**:
- `pct_atingimento` e `status_meta` calculados
- Metas vinculadas à hierarquia operacional
- Meses diferentes convivem sem conflito

---

### US-028: DAG Airflow — Transformação Silver
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Criar `airflow/dags/dag_transformation.py`**:
   ```python
   @dag(
       dag_id="transformation_silver_daily",
       schedule="0 7 * * *",  # 7h, após ingestão
       start_date=datetime(2026, 1, 1),
       catchup=False,
       tags=["transformation", "silver"],
   )
   def transformation_silver():

       @task_group(group_id="cadastros_silver")
       def transform_cadastros():
           # Cadastros primeiro (dimensões são dependência das transacionais)
           ...

       @task_group(group_id="transacionais_silver")
       def transform_transacionais():
           # Após cadastros
           ...

       transform_cadastros() >> transform_transacionais()
   ```

2. **Dependência com DAG de ingestão**:
   ```python
   from airflow.sensors.external_task import ExternalTaskSensor
   wait_ingestion = ExternalTaskSensor(
       task_id="wait_ingestion",
       external_dag_id="ingestion_daily",
       mode="reschedule",
   )
   ```

**Critério de aceite**:
- DAG executa após ingestão
- Cadastros processados antes de transacionais
- Cada task com logs e reconciliação

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Silver Notas Operacionais (com ACF/ASF e atraso) | |
| Silver Entregas de Fatura (com Haversine) | |
| Silver Pagamentos (com inadimplência) | |
| Silver Cadastros (7 tabelas conformadas) | |
| Silver Metas Operacionais | |
| DAG Airflow de transformação Silver | |
| UDF Haversine | |
| Validação de integridade referencial | |

## Verificação End-to-End

```sql
-- 1. Conferir tipagem
DESCRIBE iceberg.silver.notas_operacionais;

-- 2. Conferir classificação ACF/ASF
SELECT classificacao_acf_asf, COUNT(*)
FROM iceberg.silver.notas_operacionais
GROUP BY 1;

-- 3. Conferir status de atraso
SELECT status_atraso, COUNT(*), AVG(dias_atraso)
FROM iceberg.silver.notas_operacionais
GROUP BY 1;

-- 4. Conferir integridade referencial
SELECT COUNT(*) AS orphans
FROM iceberg.silver.notas_operacionais n
LEFT JOIN iceberg.silver.cadastro_bases b ON n.cod_base = b.cod_base
WHERE b.cod_base IS NULL;

-- 5. Reconciliação Bronze vs Silver
SELECT
    'bronze' AS layer, COUNT(*) FROM iceberg.bronze.notas_operacionais
UNION ALL
SELECT
    'silver', COUNT(*) FROM iceberg.silver.notas_operacionais;
```
