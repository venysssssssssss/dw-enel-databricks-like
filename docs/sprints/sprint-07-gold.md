# Sprint 07 — Gold Layer: Modelagem Dimensional

**Fase**: 3 — Gold & Consumo
**Duração**: 2 semanas
**Objetivo**: Construir a camada Gold com modelo estrela completo usando dbt Core — dimensões conformadas e todas as tabelas fato prioritárias.

**Pré-requisito**: Sprint 06 completa (Silver com qualidade validada)

---

## Backlog da Sprint

### US-033: dbt — Setup do Projeto
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Inicializar projeto dbt**:
   ```bash
   cd dbt/
   dbt init enel_gold
   ```

2. **Configurar `dbt_project.yml`**:
   ```yaml
   name: 'enel_gold'
   version: '1.0.0'
   profile: 'enel_trino'
   model-paths: ["models"]
   test-paths: ["tests"]
   macro-paths: ["macros"]
   seed-paths: ["seeds"]

   models:
     enel_gold:
       staging:
         +materialized: view
         +schema: staging
       dimensions:
         +materialized: table
         +schema: gold
       marts:
         +materialized: incremental
         +schema: gold
         +incremental_strategy: merge
   ```

3. **Configurar `profiles.yml`** (conexão Trino):
   ```yaml
   enel_trino:
     target: dev
     outputs:
       dev:
         type: trino
         method: none
         host: localhost
         port: 8443
         user: enel
         catalog: iceberg
         schema: gold
         threads: 2
   ```

4. **Criar macros compartilhadas**:

   `macros/generate_surrogate_key.sql`:
   ```sql
   {% macro generate_surrogate_key(field) %}
       {{ dbt_utils.generate_surrogate_key([field]) }}
   {% endmacro %}
   ```

   `macros/current_timestamp.sql`:
   ```sql
   {% macro safe_current_timestamp() %}
       CAST(NOW() AS TIMESTAMP)
   {% endmacro %}
   ```

**Critério de aceite**:
- `dbt debug` passa sem erros
- `dbt run --models staging` funciona
- Conexão Trino → Iceberg Silver validada

---

### US-034: Dimensões Conformadas
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **`models/dimensions/dim_tempo.sql`**:
   ```sql
   {{
       config(
           materialized='table',
           unique_key='sk_tempo'
       )
   }}

   -- Populada via seed ou script Python
   -- Contém: data, dia_semana, dia_mes, mes, trimestre, semestre, ano,
   --         nome_dia_semana, nome_mes, flag_feriado, flag_dia_util,
   --         uf_feriado (feriados estaduais por UF)
   SELECT
       {{ generate_surrogate_key('data_ref') }} AS sk_tempo,
       data_ref AS data,
       EXTRACT(DOW FROM data_ref) AS dia_semana,
       EXTRACT(DAY FROM data_ref) AS dia_mes,
       EXTRACT(MONTH FROM data_ref) AS mes,
       EXTRACT(QUARTER FROM data_ref) AS trimestre,
       EXTRACT(YEAR FROM data_ref) AS ano,
       CASE EXTRACT(DOW FROM data_ref)
           WHEN 0 THEN 'Domingo' WHEN 1 THEN 'Segunda'
           WHEN 2 THEN 'Terça' WHEN 3 THEN 'Quarta'
           WHEN 4 THEN 'Quinta' WHEN 5 THEN 'Sexta'
           WHEN 6 THEN 'Sábado'
       END AS nome_dia_semana,
       FORMAT_DATETIME(data_ref, 'MMMM') AS nome_mes,
       CONCAT(CAST(EXTRACT(YEAR FROM data_ref) AS VARCHAR), '-',
              LPAD(CAST(EXTRACT(MONTH FROM data_ref) AS VARCHAR), 2, '0')) AS ano_mes,
       {{ safe_current_timestamp() }} AS _loaded_at
   FROM {{ ref('seed_dim_tempo') }}
   ```

2. **`models/dimensions/dim_distribuidora.sql`**:
   ```sql
   {{
       config(materialized='table', unique_key='sk_distribuidora')
   }}

   SELECT
       {{ generate_surrogate_key('cod_distribuidora') }} AS sk_distribuidora,
       cod_distribuidora,
       nome_distribuidora,
       uf,
       regiao,
       {{ safe_current_timestamp() }} AS _loaded_at
   FROM {{ source('silver', 'cadastro_distribuidoras') }}
   ```

3. **Criar todas as dimensões** (ver `docs/architecture/04-data-flow.md`):
   - `dim_tempo` (seed + transformação)
   - `dim_distribuidora`
   - `dim_ut` (FK para distribuidora)
   - `dim_co` (FK para UT)
   - `dim_base` (FK para CO)
   - `dim_lote` (FK para base)
   - `dim_instalacao`
   - `dim_uc`
   - `dim_colaborador`
   - `dim_risco` (ACF/ASF + flag_risco — SCD1)

4. **Testes dbt para cada dimensão**:
   ```yaml
   # models/dimensions/schema.yml
   models:
     - name: dim_distribuidora
       columns:
         - name: sk_distribuidora
           tests:
             - unique
             - not_null
         - name: cod_distribuidora
           tests:
             - unique
             - not_null

     - name: dim_ut
       columns:
         - name: sk_ut
           tests: [unique, not_null]
         - name: cod_distribuidora
           tests:
             - relationships:
                 to: ref('dim_distribuidora')
                 field: cod_distribuidora
   ```

**Critério de aceite**:
- 10 dimensões criadas e populadas
- `dbt test` passa para todas as dimensões
- Surrogate keys geradas e únicas
- Hierarquia organizacional íntegra (FK tests passando)

---

### US-035: Tabelas Fato — Notas Operacionais e Efetividade
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **`models/marts/fato_notas_operacionais.sql`**:
   ```sql
   {{
       config(
           materialized='incremental',
           unique_key='cod_nota',
           incremental_strategy='merge',
       )
   }}

   WITH notas AS (
       SELECT * FROM {{ source('silver', 'notas_operacionais') }}
       {% if is_incremental() %}
       WHERE _processed_at > (SELECT MAX(_loaded_at) FROM {{ this }})
       {% endif %}
   ),

   joined AS (
       SELECT
           -- Surrogate keys (lookup nas dimensões)
           dt.sk_tempo,
           dd.sk_distribuidora,
           du.sk_ut,
           dc.sk_co,
           db.sk_base,
           dl.sk_lote,
           di.sk_instalacao,
           duc.sk_uc,
           dcol.sk_colaborador,
           dr.sk_risco,

           -- Natural key
           n.cod_nota,

           -- Métricas
           n.dias_atraso,
           CASE WHEN n.status_atraso = 'NO_PRAZO' THEN TRUE ELSE FALSE END AS flag_no_prazo,
           CASE WHEN n.status IN ('EXECUTADA', 'FECHADA') THEN TRUE ELSE FALSE END AS flag_executada,
           CASE WHEN n.status_atraso = 'ATRASADO' THEN TRUE ELSE FALSE END AS flag_atrasada,
           CASE WHEN n.status = 'DEVOLVIDA' THEN TRUE ELSE FALSE END AS flag_devolvida,
           CASE WHEN n.status = 'CANCELADA' THEN TRUE ELSE FALSE END AS flag_cancelada,

           -- Contexto
           n.tipo_servico,
           n.status AS status_nota,
           n.status_atraso,
           n.classificacao_acf_asf,

           -- Metadados
           n._run_id AS _source_run_id,
           {{ safe_current_timestamp() }} AS _loaded_at

       FROM notas n
       LEFT JOIN {{ ref('dim_tempo') }} dt
           ON n.data_criacao = dt.data
       LEFT JOIN {{ ref('dim_distribuidora') }} dd
           ON n.cod_distribuidora = dd.cod_distribuidora
       LEFT JOIN {{ ref('dim_ut') }} du
           ON n.cod_ut = du.cod_ut
       LEFT JOIN {{ ref('dim_co') }} dc
           ON n.cod_co = dc.cod_co
       LEFT JOIN {{ ref('dim_base') }} db
           ON n.cod_base = db.cod_base
       LEFT JOIN {{ ref('dim_lote') }} dl
           ON n.cod_lote = dl.cod_lote
       LEFT JOIN {{ ref('dim_instalacao') }} di
           ON n.cod_instalacao = di.cod_instalacao
       LEFT JOIN {{ ref('dim_uc') }} duc
           ON n.cod_uc = duc.cod_uc
       LEFT JOIN {{ ref('dim_colaborador') }} dcol
           ON n.cod_colaborador = dcol.cod_colaborador
       LEFT JOIN {{ ref('dim_risco') }} dr
           ON n.classificacao_acf_asf = dr.classificacao_acf_asf
           AND n.flag_risco = dr.flag_risco
   )

   SELECT * FROM joined
   ```

2. **`models/marts/fato_efetividade.sql`** — efetividade por base/dia:
   ```sql
   -- Agregação diária de efetividade por base
   SELECT
       dt.sk_tempo,
       db.sk_base,
       dd.sk_distribuidora,

       COUNT(*) AS total_notas,
       SUM(CASE WHEN flag_executada THEN 1 ELSE 0 END) AS notas_executadas,
       SUM(CASE WHEN flag_no_prazo THEN 1 ELSE 0 END) AS notas_no_prazo,
       SUM(CASE WHEN flag_devolvida THEN 1 ELSE 0 END) AS notas_devolvidas,

       ROUND(100.0 * SUM(flag_executada::INT) / COUNT(*), 2) AS efetividade_bruta_pct,
       ROUND(100.0 * SUM(flag_no_prazo::INT) / COUNT(*), 2) AS efetividade_liquida_pct,
       ROUND(100.0 * SUM(flag_devolvida::INT) / COUNT(*), 2) AS taxa_devolucao_pct,

       {{ safe_current_timestamp() }} AS _loaded_at
   FROM {{ ref('fato_notas_operacionais') }} f
   JOIN {{ ref('dim_tempo') }} dt ON f.sk_tempo = dt.sk_tempo
   JOIN {{ ref('dim_base') }} db ON f.sk_base = db.sk_base
   JOIN {{ ref('dim_distribuidora') }} dd ON f.sk_distribuidora = dd.sk_distribuidora
   GROUP BY 1, 2, 3
   ```

3. **Testes para fatos**:
   ```yaml
   models:
     - name: fato_notas_operacionais
       columns:
         - name: cod_nota
           tests: [unique, not_null]
         - name: sk_tempo
           tests: [not_null, relationships: {to: ref('dim_tempo'), field: sk_tempo}]
         - name: dias_atraso
           tests:
             - dbt_utils.accepted_range:
                 min_value: 0
                 max_value: 365
   ```

**Critério de aceite**:
- Fato notas com todas as SKs populadas
- Fato efetividade com métricas calculadas
- Incremental merge funcional (re-execução não duplica)
- `dbt test` passa para todos os fatos

---

### US-036: Tabelas Fato — Entrega, Pagamento e Metas
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **`models/marts/fato_entrega_fatura.sql`**:
   - Join com dimensões
   - Métricas: `flag_entregue`, `dias_para_entrega`, `flag_antes_vencimento`, `flag_dentro_coordenada`, `distancia_metros`

2. **`models/marts/fato_pagamento.sql`**:
   - Join com dimensões
   - Métricas: `valor_fatura`, `valor_pago`, `flag_inadimplente`, `dias_atraso_pagamento`

3. **`models/marts/fato_entrega_vs_coord.sql`**:
   - Agregação de entregas com análise de coordenada
   - Métricas: `taxa_coordenada_pct`, `distancia_media`

4. **`models/marts/fato_nao_lidos.sql`**:
   - Métricas: `flag_lido`, `motivo_nao_leitura`, `flag_releitura`

5. **`models/marts/fato_metas.sql`**:
   - Métricas: `valor_meta`, `valor_realizado`, `pct_atingimento`, `status_meta`, `gap_absoluto`

6. **Testes dbt para todos os fatos**

**Critério de aceite**:
- 5 tabelas fato adicionais criadas
- Métricas calculadas conforme `docs/business-rules/03-operational-metrics.md`
- Todos os testes dbt passando
- `dbt docs generate && dbt docs serve` mostra grafo completo

---

### US-037: DAG Airflow — dbt Gold
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Criar `airflow/dags/dag_dbt.py`**:
   ```python
   @dag(
       dag_id="dbt_gold_daily",
       schedule="0 9 * * *",  # 9h, após quality checks
       tags=["dbt", "gold"],
   )
   def dbt_gold():

       @task()
       def dbt_seed():
           """Executa seeds (dim_tempo, etc)."""
           subprocess.run(["dbt", "seed", "--project-dir", "/opt/airflow/dbt"], check=True)

       @task()
       def dbt_run_dimensions():
           subprocess.run(["dbt", "run", "--select", "dimensions", "--project-dir", "/opt/airflow/dbt"], check=True)

       @task()
       def dbt_run_marts():
           subprocess.run(["dbt", "run", "--select", "marts", "--project-dir", "/opt/airflow/dbt"], check=True)

       @task()
       def dbt_test():
           subprocess.run(["dbt", "test", "--project-dir", "/opt/airflow/dbt"], check=True)

       dbt_seed() >> dbt_run_dimensions() >> dbt_run_marts() >> dbt_test()
   ```

**Critério de aceite**:
- DAG executa dbt em sequência: seed → dimensions → marts → test
- Dependência com DAG de qualidade
- Falha em dbt test marca DAG como failed

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Projeto dbt configurado com Trino | |
| 10 dimensões conformadas | |
| 7 tabelas fato | |
| Testes dbt (unique, not_null, relationships, range) | |
| DAG Airflow para dbt Gold | |
| dbt docs gerado | |
| Reconciliação Silver→Gold | |
