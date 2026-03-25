# Feature Engineering — Especificação Completa

## Princípios

1. Features são calculadas na **Gold layer** e materializadas como tabelas de features no MinIO
2. Toda feature tem **documentação** (nome, tipo, lógica, fonte)
3. Features usam **dados historicizados** — nunca dados futuros (data leakage prevention)
4. Features temporais respeitam **janelas de observação** configuráveis

---

## Features para Predição de Atraso de Entrega

### Features da Nota (ponto-in-time)

| Feature | Tipo | Lógica |
|---|---|---|
| `tipo_servico` | Categórica | Tipo de serviço da nota |
| `classificacao_acf_asf` | Categórica | Classificação ACF/ASF |
| `flag_risco` | Binária | Se a nota é de risco |
| `dias_ate_vencimento` | Numérica | `data_prevista - data_criacao` em dias úteis |
| `dia_semana_criacao` | Categórica | Dia da semana em que a nota foi criada |
| `dia_semana_previsto` | Categórica | Dia da semana previsto para execução |
| `hora_criacao` | Numérica | Hora de criação (0-23) |
| `flag_fim_de_mes` | Binária | Se a data prevista está nos últimos 5 dias úteis do mês |
| `flag_inicio_de_mes` | Binária | Se a data prevista está nos primeiros 5 dias úteis do mês |

### Features do Histórico da UC

| Feature | Tipo | Lógica | Janela |
|---|---|---|---|
| `qtd_notas_uc_30d` | Numérica | Qtd de notas na UC nos últimos 30 dias | 30 dias |
| `qtd_notas_uc_90d` | Numérica | Qtd de notas na UC nos últimos 90 dias | 90 dias |
| `taxa_atraso_uc_90d` | Numérica | % de notas atrasadas na UC | 90 dias |
| `taxa_atraso_uc_180d` | Numérica | % de notas atrasadas na UC | 180 dias |
| `media_dias_atraso_uc` | Numérica | Média de dias de atraso na UC | 180 dias |
| `max_dias_atraso_uc` | Numérica | Máximo atraso na UC | 180 dias |
| `qtd_devolucoes_uc_90d` | Numérica | Devoluções na UC | 90 dias |
| `dias_desde_ultima_nota_uc` | Numérica | Dias desde a última nota executada na UC | - |

### Features da Base/CO

| Feature | Tipo | Lógica | Janela |
|---|---|---|---|
| `taxa_atraso_base_7d` | Numérica | % de atraso da base nos últimos 7 dias | 7 dias |
| `taxa_atraso_base_30d` | Numérica | % de atraso da base nos últimos 30 dias | 30 dias |
| `volume_notas_base_dia` | Numérica | Qtd de notas atribuídas à base no dia | 1 dia |
| `carga_colaboradores_base` | Numérica | Notas por colaborador ativo na base | 1 dia |
| `taxa_atraso_co_30d` | Numérica | % de atraso do CO | 30 dias |
| `efetividade_base_7d` | Numérica | Efetividade da base últimos 7 dias | 7 dias |
| `ranking_base_atraso` | Numérica | Ranking da base por taxa de atraso no CO | 30 dias |

### Features do Colaborador

| Feature | Tipo | Lógica | Janela |
|---|---|---|---|
| `taxa_atraso_colaborador_30d` | Numérica | % de atraso do colaborador | 30 dias |
| `produtividade_colaborador_7d` | Numérica | Notas executadas por dia | 7 dias |
| `taxa_devolucao_colaborador_30d` | Numérica | % de devoluções | 30 dias |
| `experiencia_dias` | Numérica | Dias desde primeira nota registrada | - |
| `notas_mesmo_tipo_30d` | Numérica | Notas do mesmo tipo executadas | 30 dias |

### Features Contextuais

| Feature | Tipo | Lógica |
|---|---|---|
| `flag_feriado_proximo` | Binária | Se há feriado nos próximos 2 dias úteis |
| `flag_chuva_prevista` | Binária | Se há previsão de chuva (futuro, quando disponível) |
| `pct_meta_atual_base` | Numérica | % atingimento da meta da base no momento |
| `gap_meta_base` | Numérica | Diferença entre realizado e meta |

---

## Features para Predição de Não Pagamento

### Features da Fatura

| Feature | Tipo | Lógica |
|---|---|---|
| `valor_fatura` | Numérica | Valor da fatura em R$ |
| `valor_fatura_log` | Numérica | log(valor_fatura + 1) — reduz skewness |
| `mes_referencia` | Categórica | Mês de referência da fatura |
| `dias_ate_vencimento` | Numérica | Dias entre emissão e vencimento |
| `dia_semana_vencimento` | Categórica | Dia da semana do vencimento |

### Features do Histórico de Pagamento da UC

| Feature | Tipo | Lógica | Janela |
|---|---|---|---|
| `qtd_faturas_pagas_12m` | Numérica | Faturas pagas no prazo | 12 meses |
| `qtd_faturas_atrasadas_12m` | Numérica | Faturas pagas com atraso | 12 meses |
| `qtd_faturas_inadimplentes_12m` | Numérica | Faturas nunca pagas | 12 meses |
| `taxa_inadimplencia_12m` | Numérica | % de inadimplência | 12 meses |
| `taxa_inadimplencia_6m` | Numérica | % de inadimplência | 6 meses |
| `taxa_inadimplencia_3m` | Numérica | % de inadimplência recente | 3 meses |
| `media_dias_atraso_pgto` | Numérica | Média de dias de atraso no pagamento | 12 meses |
| `max_dias_atraso_pgto` | Numérica | Maior atraso de pagamento | 12 meses |
| `valor_medio_fatura_12m` | Numérica | Valor médio das faturas | 12 meses |
| `variacao_valor_fatura` | Numérica | Variação do valor vs média | - |
| `meses_consecutivos_inadimplente` | Numérica | Meses seguidos sem pagar | - |
| `meses_desde_ultimo_pagamento` | Numérica | Meses desde último pagamento | - |
| `flag_historico_negociacao` | Binária | Se já teve negociação de débito | - |

### Features da UC

| Feature | Tipo | Lógica |
|---|---|---|
| `classe_consumo` | Categórica | Residencial, comercial, industrial |
| `tipo_ligacao` | Categórica | Monofásica, bifásica, trifásica |
| `consumo_medio_kwh_6m` | Numérica | Consumo médio | 6 meses |
| `variacao_consumo_3m` | Numérica | % variação do consumo recente |
| `antiguidade_uc_meses` | Numérica | Meses desde criação da UC |

### Features Geográficas/Regionais

| Feature | Tipo | Lógica |
|---|---|---|
| `taxa_inadimplencia_regiao_30d` | Numérica | % inadimplência no CO/base |
| `renda_media_estimada_regiao` | Numérica | Proxy por consumo médio da região |
| `densidade_ucs_base` | Numérica | Qtd de UCs por base |

---

## Features para Projeção de Meta

### Features de Progresso

| Feature | Tipo | Lógica |
|---|---|---|
| `pct_dias_uteis_decorridos` | Numérica | Fração do mês útil passada |
| `pct_realizado_atual` | Numérica | Realizado / Meta |
| `taxa_diaria_necessaria` | Numérica | (Meta - Realizado) / Dias úteis restantes |
| `taxa_diaria_atual` | Numérica | Realizado / Dias úteis decorridos |
| `gap_velocidade` | Numérica | Taxa atual - Taxa necessária |
| `aceleracao_7d` | Numérica | Diferença entre taxa dos últimos 7d e taxa geral |

### Features Históricas da Meta

| Feature | Tipo | Lógica | Janela |
|---|---|---|---|
| `pct_atingimento_mes_anterior` | Numérica | Atingimento mês anterior | 1 mês |
| `pct_atingimento_mesmo_mes_ano_anterior` | Numérica | Sazonalidade anual | 12 meses |
| `media_atingimento_3m` | Numérica | Média de atingimento | 3 meses |
| `std_atingimento_6m` | Numérica | Volatilidade do atingimento | 6 meses |
| `qtd_meses_meta_atingida_6m` | Numérica | Meses com meta batida | 6 meses |
| `pct_mesmo_ponto_mes_anterior` | Numérica | Realizado no mesmo dia do mês anterior | - |
| `delta_vs_mes_anterior` | Numérica | Diferença de progresso vs mês anterior | - |

### Features da Base

| Feature | Tipo | Lógica |
|---|---|---|
| `qtd_colaboradores_ativos` | Numérica | Colaboradores com nota no mês |
| `taxa_absenteismo_estimada` | Numérica | % dias sem execução por colaborador |
| `volume_notas_pendentes` | Numérica | Notas não executadas no momento |
| `ranking_base_atingimento` | Numérica | Ranking no CO por atingimento |

---

## Feature Store — Materialização

### Estrutura no MinIO

```
s3://lakehouse/ml/features/
├── feat_atraso/
│   ├── _partition_date=2026-03-25/
│   │   └── features.parquet
│   └── _metadata/
│       └── feature_manifest.json
├── feat_inadimplencia/
│   └── ...
└── feat_metas/
    └── ...
```

### Manifest de Features

```json
{
  "feature_set": "feat_atraso",
  "version": "1.0.0",
  "created_at": "2026-03-25T10:00:00Z",
  "entity_key": "cod_nota",
  "temporal_key": "data_criacao",
  "features": [
    {
      "name": "taxa_atraso_base_7d",
      "dtype": "float64",
      "description": "Taxa de atraso da base nos últimos 7 dias",
      "source_tables": ["silver.notas_operacionais"],
      "window_days": 7,
      "null_rate_expected": 0.02
    }
  ],
  "row_count": 150000,
  "quality_checks_passed": true
}
```

### Pipeline de Feature Engineering

```
Airflow DAG: feature_engineering_daily
│
├── Task 1: Calcular features de nota (Silver → Features)
├── Task 2: Calcular features de UC (Silver → Features)
├── Task 3: Calcular features de base/CO (Silver/Gold → Features)
├── Task 4: Calcular features de colaborador (Silver → Features)
├── Task 5: Join features por entity_key
├── Task 6: Validar features (Great Expectations)
└── Task 7: Materializar no MinIO (Iceberg table)
```

---

## Prevenção de Data Leakage

### Checklist Obrigatório

- [ ] Features calculadas usando apenas dados **anteriores** à data de referência
- [ ] Nenhuma feature usa informação do outcome (target)
- [ ] Features de janela respeitam `observation_date - window_days`
- [ ] Split temporal no treino (nunca random split)
- [ ] Features de "futuro" (previsão de chuva, feriados) são tratadas como known-in-advance

### Padrão de Cálculo com Point-in-Time

```python
def calcular_features_pit(df_notas, df_historico, observation_date):
    """
    Calcula features usando apenas dados anteriores a observation_date.
    Point-in-Time correct.
    """
    historico_valido = df_historico.filter(
        col('data_evento') < observation_date
    )

    features = (
        historico_valido
        .filter(col('data_evento') >= date_sub(observation_date, 90))
        .groupBy('cod_uc')
        .agg(
            count('*').alias('qtd_notas_uc_90d'),
            avg(col('flag_atraso').cast('int')).alias('taxa_atraso_uc_90d'),
        )
    )

    return df_notas.join(features, on='cod_uc', how='left')
```
