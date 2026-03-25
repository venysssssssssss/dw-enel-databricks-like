# Sprint 08 — BI: Superset Dashboards

**Fase**: 3 — Gold & Consumo
**Duração**: 2 semanas
**Objetivo**: Configurar Apache Superset, conectar à camada Gold via Trino e criar os dashboards gerenciais prioritários.

**Pré-requisito**: Sprint 07 completa (Gold layer com fatos e dimensões)

---

## Backlog da Sprint

### US-038: Superset — Setup e Configuração
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Adicionar Superset ao Docker Compose**:
   ```yaml
   superset:
     image: apache/superset:4.0.1
     environment:
       SUPERSET_SECRET_KEY: ${SUPERSET_SECRET_KEY}
       DATABASE_URL: postgresql://enel:enel123@postgres:5432/superset
     ports:
       - "8088:8088"
     depends_on:
       postgres:
         condition: service_healthy
     deploy:
       resources:
         limits:
           memory: 768M
     volumes:
       - ./config/superset/superset_config.py:/app/pythonpath/superset_config.py
   ```

2. **Criar `infra/config/superset/superset_config.py`**:
   ```python
   SQLALCHEMY_DATABASE_URI = "postgresql://enel:enel123@postgres:5432/superset"
   SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "changeme")
   WTF_CSRF_ENABLED = True
   ENABLE_PROXY_FIX = True

   # Limites para hardware limitado
   SUPERSET_WEBSERVER_TIMEOUT = 120
   SQL_MAX_ROW = 50000
   ROW_LIMIT = 10000
   SAMPLES_ROW_LIMIT = 1000
   ```

3. **Inicializar Superset**:
   ```bash
   docker compose exec superset superset db upgrade
   docker compose exec superset superset fab create-admin \
       --username admin --password admin \
       --firstname Admin --lastname User --email admin@enel.local
   docker compose exec superset superset init
   ```

4. **Configurar database connection (Trino)**:
   - SQLAlchemy URI: `trino://enel@trino:8080/iceberg/gold`
   - Testar conexão via Superset UI

**Critério de aceite**:
- Superset acessível em `http://localhost:8088`
- Conexão com Trino funcionando
- Tabelas Gold visíveis no SQL Lab
- Memória dentro do limite (768MB)

---

### US-039: Datasets Superset
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Registrar datasets para cada tabela Gold**:
   - `fato_notas_operacionais` (joinado com dimensões via SQL Lab)
   - `fato_efetividade`
   - `fato_entrega_fatura`
   - `fato_pagamento`
   - `fato_metas`
   - `fato_nao_lidos`

2. **Criar virtual datasets** (queries pré-montadas para performance):

   **Dataset: Visão Geral Operacional**:
   ```sql
   SELECT
       dt.ano_mes,
       dd.nome_distribuidora,
       du.nome_ut,
       dc.nome_co,
       db.nome_base,
       COUNT(*) AS total_notas,
       SUM(f.flag_executada::INT) AS executadas,
       SUM(f.flag_no_prazo::INT) AS no_prazo,
       SUM(f.flag_atrasada::INT) AS atrasadas,
       ROUND(100.0 * SUM(f.flag_no_prazo::INT) / COUNT(*), 2) AS efetividade_pct,
       ROUND(AVG(f.dias_atraso), 1) AS atraso_medio
   FROM gold.fato_notas_operacionais f
   JOIN gold.dim_tempo dt ON f.sk_tempo = dt.sk_tempo
   JOIN gold.dim_distribuidora dd ON f.sk_distribuidora = dd.sk_distribuidora
   JOIN gold.dim_ut du ON f.sk_ut = du.sk_ut
   JOIN gold.dim_co dc ON f.sk_co = dc.sk_co
   JOIN gold.dim_base db ON f.sk_base = db.sk_base
   GROUP BY 1, 2, 3, 4, 5
   ```

   **Dataset: Resumo de Metas**:
   ```sql
   SELECT
       dt.ano_mes,
       dd.nome_distribuidora,
       db.nome_base,
       m.valor_meta,
       m.valor_realizado,
       m.pct_atingimento,
       m.status_meta
   FROM gold.fato_metas m
   JOIN gold.dim_tempo dt ON m.sk_tempo = dt.sk_tempo
   JOIN gold.dim_distribuidora dd ON m.sk_distribuidora = dd.sk_distribuidora
   JOIN gold.dim_base db ON m.sk_base = db.sk_base
   ```

3. **Configurar métricas calculadas** nos datasets (avg, sum, count)

**Critério de aceite**:
- Todos os datasets registrados
- Queries executam em < 5 segundos
- Filtros de distribuidora/UT/CO/base funcionam

---

### US-040: Dashboard — Visão Geral Operacional
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar dashboard "Visão Geral Operacional"** com os seguintes charts:

   **Filtros globais** (barra superior):
   - Distribuidora (dropdown)
   - UT (dropdown, dependente de distribuidora)
   - CO (dropdown, dependente de UT)
   - Base/Polo (dropdown, dependente de CO)
   - Período (date range picker)

   **KPIs** (cards no topo):
   - Total de notas no período
   - Efetividade líquida (%)
   - Atraso médio (dias)
   - Taxa de devolução (%)

   **Charts**:
   - **Efetividade por mês** (line chart) — evolução temporal
   - **Distribuição ACF/ASF** (pie chart) — proporção por classificação
   - **Top 10 bases com mais atraso** (bar chart horizontal)
   - **Status de atraso** (stacked bar) — no prazo / pendente / atrasado por mês
   - **Heatmap Atraso por CO × Mês** — identifica padrões espaciais-temporais
   - **Tabela detalhada** — últimas 50 notas atrasadas com dados de contexto

**Critério de aceite**:
- Dashboard funcional com filtros cross-filter
- Atualização automática a cada 30 minutos
- Todos os KPIs calculam corretamente
- Filtro de hierarquia funciona (distribuidora → UT → CO → base)

---

### US-041: Dashboard — Entrega de Faturas
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Criar dashboard "Entrega de Faturas"**:

   **KPIs**:
   - Taxa de entrega (%)
   - Taxa dentro da coordenada (%)
   - Prazo médio de entrega (dias)
   - Entregas antes do vencimento (%)

   **Charts**:
   - Evolução da taxa de entrega por mês
   - Mapa de calor por base (se Superset suportar mapa)
   - Distribuição de distância entrega vs coordenada (histogram)
   - Top bases com menor taxa de entrega

---

### US-042: Dashboard — Metas e Projeção
**Prioridade**: P0
**Story Points**: 3

**Tarefas**:

1. **Criar dashboard "Metas Operacionais"**:

   **KPIs**:
   - Metas atingidas (%)
   - Metas em risco (%)
   - Metas críticas (%)
   - Gap médio para meta (%)

   **Charts**:
   - Gauge charts por meta (atingimento %)
   - Comparativo meta vs realizado por base (grouped bar)
   - Evolução mensal de atingimento
   - Tabela: bases com meta crítica (< 70%)

---

### US-043: Dashboard — Inadimplência
**Prioridade**: P1
**Story Points**: 3

**Tarefas**:

1. **Criar dashboard "Inadimplência"**:

   **KPIs**:
   - Taxa de inadimplência (%)
   - Valor total em aberto (R$)
   - UCs inadimplentes (count)

   **Charts**:
   - Aging de inadimplência (stacked bar: 30, 60, 90, 90+ dias)
   - Evolução da taxa de inadimplência por mês
   - Top regiões com mais inadimplência
   - Perfil de inadimplência (crônico, recorrente, eventual)

---

### US-044: Export Templates via Superset
**Prioridade**: P1
**Story Points**: 2

**Tarefas**:

1. **Configurar saved queries** no SQL Lab para exports comuns:
   - "Notas atrasadas por base e período"
   - "Entregas fora da coordenada"
   - "UCs inadimplentes há 90+ dias"
   - "Efetividade por colaborador"

2. **Documentar** como usar SQL Lab para exports ad-hoc

**Critério de aceite**:
- Queries salvas acessíveis no SQL Lab
- Export CSV funciona para resultados < 50k linhas

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Superset configurado com Trino | |
| Datasets registrados para todas as tabelas Gold | |
| Dashboard: Visão Geral Operacional | |
| Dashboard: Entrega de Faturas | |
| Dashboard: Metas e Projeção | |
| Dashboard: Inadimplência | |
| Saved queries para exports | |

## Verificação

```
1. Acessar http://localhost:8088
2. Login com admin/admin
3. Abrir cada dashboard
4. Testar filtros: selecionar distribuidora → verificar cascata para UT → CO → base
5. Verificar KPIs contra queries diretas no Trino
6. Testar export CSV via SQL Lab
7. Verificar refresh automático (se configurado)
```
