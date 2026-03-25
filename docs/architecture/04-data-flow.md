# Fluxo de Dados Detalhado

## 1. Ingestão (Fontes → Bronze)

### Tipos de Carga por Domínio

| Domínio | Tipo de Carga | Frequência | Estratégia |
|---|---|---|---|
| Cadastros/mestres (distribuidora, UT, CO, base) | Snapshot completo | Diária | Substituição total da partição |
| Notas operacionais | Incremental por watermark | Diária | `WHERE data_alteracao > last_watermark` |
| Entregas de fatura | Incremental por watermark | Diária | `WHERE data_alteracao > last_watermark` |
| Pagamentos | Incremental por watermark | Diária | `WHERE data_processamento > last_watermark` |
| Metas operacionais | Snapshot mensal | Mensal | Partição por mês de referência |
| Fechamentos mensais | Snapshot mensal | Mensal | Imutável após fechamento |
| Efetividade operacional | Incremental | Diária | Append com deduplicação na Silver |

### Schema Bronze (metadados técnicos)

Cada tabela Bronze inclui colunas técnicas obrigatórias:

```
_run_id          STRING    -- UUID da execução do pipeline
_ingested_at     TIMESTAMP -- momento exato da ingestão
_source_file     STRING    -- arquivo/endpoint/query de origem
_source_hash     STRING    -- SHA-256 do conteúdo original
_partition_date  DATE      -- data lógica da partição
```

Os dados de negócio são preservados **exatamente** como chegaram — sem transformação, sem casting, sem deduplicação.

### Formato de Armazenamento

```
s3://lakehouse/
  bronze/
    notas_operacionais/
      _partition_date=2026-03-25/
        part-00000-{uuid}.parquet
        part-00001-{uuid}.parquet
    entregas_fatura/
      _partition_date=2026-03-25/
        ...
    cadastros/
      distribuidoras/
        _partition_date=2026-03-25/
          ...
```

## 2. Curadoria (Bronze → Silver)

### Transformações Aplicadas

| Transformação | Descrição | Exemplo |
|---|---|---|
| Tipagem | Cast para tipos corretos | `STRING "2026-03-25"` → `DATE` |
| Normalização de chaves | Padronizar identificadores | `UC`, `cod_uc`, `unidade_consumo` → `cod_uc` |
| Deduplicação | Remover registros duplicados | Manter mais recente por `(cod_uc, data_referencia)` |
| Null handling | Tratar valores ausentes | Default values ou flags explícitos |
| Padronização textual | Normalizar strings | `UPPER()`, `TRIM()`, remover acentos em chaves |
| Validação de domínio | Garantir valores válidos | `status IN ('ATIVO', 'INATIVO', 'SUSPENSO')` |
| Historização (SCD2) | Manter histórico de mudanças | `valid_from`, `valid_to`, `is_current` |

### Schema Silver (exemplo: notas operacionais)

```sql
CREATE TABLE silver.notas_operacionais (
    -- Chaves
    cod_nota            BIGINT       NOT NULL,
    cod_uc              BIGINT       NOT NULL,
    cod_instalacao      BIGINT       NOT NULL,

    -- Dimensões operacionais
    cod_distribuidora   INTEGER      NOT NULL,
    cod_ut              INTEGER      NOT NULL,
    cod_co              INTEGER      NOT NULL,
    cod_base            INTEGER      NOT NULL,
    cod_lote            INTEGER,

    -- Classificação
    tipo_nota           STRING       NOT NULL,
    classificacao_acf   STRING,      -- 'ACF_A', 'ACF_B', 'ACF_C', etc.
    classificacao_asf   STRING,      -- 'ASF_RISCO', 'ASF_FORA_RISCO', etc.
    flag_risco          BOOLEAN      NOT NULL,

    -- Temporais
    data_criacao        DATE         NOT NULL,
    data_prevista       DATE,
    data_execucao       DATE,
    data_fechamento     DATE,

    -- Métricas
    dias_atraso         INTEGER,     -- calculado: data_execucao - data_prevista
    status_atraso       STRING,      -- 'NO_PRAZO', 'PENDENTE_NO_PRAZO', 'PENDENTE_FORA_PRAZO', 'ATRASADO'

    -- Metadados técnicos
    _run_id             STRING       NOT NULL,
    _processed_at       TIMESTAMP    NOT NULL,
    _source_run_id      STRING       NOT NULL,  -- referência ao run_id Bronze
    _valid_from         TIMESTAMP    NOT NULL,
    _valid_to           TIMESTAMP,
    _is_current         BOOLEAN      NOT NULL DEFAULT TRUE
)
PARTITIONED BY (MONTH(data_criacao))
```

## 3. Modelagem Dimensional (Silver → Gold)

### Tabelas Fato Prioritárias

| Fato | Granularidade | Métricas |
|---|---|---|
| `fato_entrega_fatura` | 1 registro por entrega por UC | qtd_entregas, flag_entregue, dias_para_entrega |
| `fato_efetividade` | 1 registro por nota por dia | flag_executada, flag_no_prazo, tempo_execucao |
| `fato_notas_operacionais` | 1 registro por nota | dias_atraso, status_atraso, classificacao |
| `fato_pagamento` | 1 registro por fatura | valor_fatura, valor_pago, flag_inadimplente |
| `fato_entrega_vs_coord` | 1 registro por entrega | flag_dentro_coordenada, distancia_km |
| `fato_nao_lidos` | 1 registro por leitura tentativa | flag_lido, motivo_nao_leitura |
| `fato_metas` | 1 registro por meta por período | meta_valor, realizado_valor, pct_atingimento |

### Dimensões Conformadas

| Dimensão | Chave Surrogate | Atributos Principais |
|---|---|---|
| `dim_tempo` | `sk_tempo` | data, dia_semana, mes, trimestre, ano, flag_feriado, flag_dia_util |
| `dim_distribuidora` | `sk_distribuidora` | cod_distribuidora, nome, uf, regiao |
| `dim_ut` | `sk_ut` | cod_ut, nome_ut, distribuidora_fk |
| `dim_co` | `sk_co` | cod_co, nome_co, ut_fk |
| `dim_base` | `sk_base` | cod_base, nome_base, co_fk, tipo (base/polo) |
| `dim_lote` | `sk_lote` | cod_lote, base_fk, tipo_servico |
| `dim_instalacao` | `sk_instalacao` | cod_instalacao, cod_uc, endereco, tipo |
| `dim_uc` | `sk_uc` | cod_uc, tipo_consumo, classe, status |
| `dim_colaborador` | `sk_colaborador` | cod_colaborador, nome, equipe, funcao |
| `dim_risco` | `sk_risco` | classificacao_acf, classificacao_asf, flag_risco, descricao |

### Modelo Estrela Principal (Notas Operacionais)

```
                     ┌────────────┐
                     │ dim_tempo  │
                     └──────┬─────┘
                            │
┌───────────────┐    ┌──────┴──────────────┐    ┌─────────────────┐
│dim_distribuidora│──│fato_notas_operacionais│──│  dim_risco      │
└───────────────┘    │                      │    └─────────────────┘
                     │  sk_tempo            │
┌───────────────┐    │  sk_distribuidora    │    ┌─────────────────┐
│   dim_ut      │────│  sk_ut               │────│  dim_base       │
└───────────────┘    │  sk_co               │    └─────────────────┘
                     │  sk_base             │
┌───────────────┐    │  sk_lote             │    ┌─────────────────┐
│   dim_co      │────│  sk_instalacao       │────│  dim_lote       │
└───────────────┘    │  sk_uc               │    └─────────────────┘
                     │  sk_colaborador      │
┌───────────────┐    │  sk_risco            │    ┌─────────────────┐
│dim_instalacao │────│                      │────│dim_colaborador  │
└───────────────┘    │  -- métricas --      │    └─────────────────┘
                     │  dias_atraso         │
┌───────────────┐    │  flag_no_prazo       │
│   dim_uc      │────│  flag_executada      │
└───────────────┘    │  qtd_retrabalho      │
                     └──────────────────────┘
```

## 4. Consumo (Gold → Aplicações)

### Superset (BI)
- Conecta via Trino (SQLAlchemy)
- Lê somente da camada Gold
- Filtros: distribuidora, UT, CO, base, período, lote
- NÃO contém regras de negócio — apenas visualização

### FastAPI (Exportação)
- Endpoints REST para download filtrado (CSV, Parquet, Excel)
- Autenticação via JWT
- Rate limiting por usuário
- Streaming para datasets grandes
- Queries via Trino (async)

### MLflow (Scoring)
- Features vêm da Gold (feature store materializada)
- Modelos treinados e versionados no MLflow
- Scoring batch via Airflow DAG
- Resultados publicados de volta na Gold como tabela de scores

## 5. Reconciliação entre Camadas

Cada execução do pipeline inclui reconciliação:

```
Bronze count  ──compare──► Silver count  ──compare──► Gold count
     │                          │                         │
     └── registros ingeridos    └── após deduplicação     └── após agregação
                                    e filtros                  e joins
```

Métricas de reconciliação armazenadas em tabela de auditoria:

```sql
CREATE TABLE audit.reconciliation_log (
    run_id          STRING,
    layer           STRING,     -- 'bronze_to_silver', 'silver_to_gold'
    table_name      STRING,
    source_count    BIGINT,
    target_count    BIGINT,
    delta_count     BIGINT,
    delta_pct       DOUBLE,
    status          STRING,     -- 'OK', 'WARNING', 'FAIL'
    threshold_pct   DOUBLE,     -- limiar configurável
    executed_at     TIMESTAMP
)
```
