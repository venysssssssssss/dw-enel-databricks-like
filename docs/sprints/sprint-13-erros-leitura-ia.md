# Sprint 13 — IA de Classificação Inteligente de Erros de Leitura

## Contexto

A ENEL nunca teve uma visão estruturada dos **erros de leitura** (subtipo crítico de reclamação). Hoje, esses erros vivem em planilhas Excel (guia `erro de leitura`), com campos livres `OBSERVAÇÃO ORDEM` e `DEVOLUTIVA` escritos por operadores — um ativo de texto não-estruturado com altíssimo sinal, desperdiçado.

O objetivo desta sprint é entregar uma **solução de IA ponta-a-ponta** que ingere, normaliza, clusteriza e classifica erros de leitura, respondendo:

- *Por que esses erros acontecem?*
- *Como acontecem? De que maneira?*
- *Com que frequência?*
- *Quais padrões existem?*
- *Eles são causa-raiz de outras reclamações?*

**Valor de produto**: taxonomia viva de causas-raiz, detecção proativa de erros sistêmicos (bairro/rota/leiturista), priorização de regiões críticas, feedback loop para capacitação de campo — algo inédito na operação da ENEL.

## Dados de Entrada

Diretório: `DESCRICOES_ENEL/`

| Arquivo | Região | Guia principal | Linhas | Observação |
|---|---|---|---|---|
| `reclamacoes_total_2026.xlsx` | CE | `erro de leitura` | ~1.490 | 2 guias (total + erro de leitura) |
| `reclamacoes_total_AGO25.xlsx` … `SET25.xlsx` (10 arquivos) | CE | `erro de leitura` | ~1.500/arq | padrão idêntico |
| `reclamacoes_total_JAN25.xlsx` | CE | `reclamacoes_CE_RJ_JAN25` | 520 | guia única, mesmo schema |
| `TRATADO Trimestre_Ordens (2).xlsx` | **SP** | `Base N1` | 12.310 | schema ligeiramente diferente (INSTALACAO str, ordem de colunas divergente) |

**Colunas-chave** (comuns):
`GRUPO`, `ORDEM`, `ASSUNTO`, `INSTALACAO`, `DT. INGRESSO`, `OBSERVAÇÃO ORDEM` (texto livre), `Status`, `DEVOLUTIVA` (texto livre, análise técnica), `Causa Raiz` (label fraco, parcialmente preenchido apenas no CE).

**Preservar ambas as guias** (erro de leitura + total): iterações futuras vão cruzar se reclamações não-leitura são *derivadas* de erros de leitura.

## Arquitetura

```
Excel (DESCRICOES_ENEL/)
  → Bronze  (Iceberg: raw + _run_id, _ingested_at, _source_region, _sheet_name)
  → Silver  (normalizado CE+SP, dedup por ORDEM, texto limpo, entidades extraídas)
  → Gold    (fato_erro_leitura + dim_causa_raiz + dim_regiao + dim_tempo)
  → Feature store (embeddings multilingual + features categóricas/temporais)
  → ML:
      (a) Topic Modeling não-supervisionado  (BERTopic)
      (b) Classificador supervisionado       (LightGBM + LR baseline, weak supervision)
      (c) Detecção de anomalias espaço-temporais (Isolation Forest + Z-score rolling)
  → API FastAPI  (/erros-leitura/classificar, /padroes, /hotspots, /{ordem})
  → Dashboard Superset  (heatmap, evolução temporal, top hotspots, drill-down)
```

## Entregáveis por Fase

### Fase 1 — Ingestão Bronze (unificada CE + SP)

- **Novo**: `src/ingestion/descricoes_enel_ingestor.py` — estende `BaseIngestor`
  - Lê **todas as guias** de cada xlsx; marca `_sheet_name` e `_data_type` (`erro_leitura` | `reclamacao_total` | `base_n1_sp`)
  - Deriva `_source_region` (`CE` | `SP`) a partir do filename (`TRATADO Trimestre_Ordens` → SP; demais → CE)
  - Metadados técnicos: `_run_id`, `_ingested_at`, `_source_hash`, `_source_file`
- **Novo**: `src/ingestion/configs/descricoes_enel.yaml` — mapping de colunas CE vs SP
- **Tabela Iceberg**: `bronze.descricoes_reclamacoes`

### Fase 2 — Silver (normalização + limpeza de texto)

- **Novo**: `src/transformation/processors/erro_leitura_normalizer.py`
  - Unifica schema CE↔SP (cast `INSTALACAO` para string; trim/upper de códigos)
  - Dedup por `(ORDEM, _source_region)`
  - **Limpeza de texto** em `OBSERVAÇÃO ORDEM` e `DEVOLUTIVA`:
    - Remove HTML (`<br>`, tags)
    - Normaliza acentos, lowercase, trim, colapsa whitespace
    - Preserva originais em `*_raw`
  - Extrai entidades via regex: telefone, CEP, protocolo, data, UC/INSTALACAO mencionada no texto
  - Flag `has_causa_raiz_label` (CE parcial; SP = null)
- **Tabela**: `silver.erro_leitura_normalizado`

### Fase 3 — Gold (modelo dimensional)

- **Novos dbt models** em `dbt/models/marts/erro_leitura/`:
  - `fato_erro_leitura.sql` — grão: 1 linha por ORDEM
  - `dim_causa_raiz.sql` — taxonomia (inicialmente das labels CE; expandida após Fase 4)
  - `dim_regiao.sql` — CE/SP + distrito/município quando extraível do texto
  - Reuso: `dim_tempo` existente
- **Métricas**: `erros_por_dia`, `erros_por_regiao`, `tempo_resolucao_medio`, `% resolvidos_com_refaturamento`, `% erros reincidentes (90d)`

### Fase 4 — NLP: descoberta de padrões (não-supervisionado)

- **Novo**: `src/ml/features/text_embeddings.py`
  - Embeddings via `sentence-transformers`
  - Modelo: `paraphrase-multilingual-MiniLM-L12-v2` (PT-BR, CPU-friendly, 118MB)
  - Concatena `OBSERVAÇÃO ORDEM` + `DEVOLUTIVA`
  - Persiste em parquet (feature store) com chave `ORDEM`
- **Novo**: `src/ml/models/erro_leitura_topic_model.py` — estende `BaseModelTrainer`
  - Topic modeling via **BERTopic** (UMAP + HDBSCAN sobre embeddings)
  - Nomeia tópicos via c-TF-IDF + amostragem representativa
  - Saída: taxonomia descoberta (ex.: *digitação*, *acesso negado*, *medidor danificado*, *leitura estimada*, *endereço divergente*)
  - Artefatos no MLflow: tópicos, palavras-chave, tamanho, exemplos

### Fase 5 — Classificador supervisionado (semi-supervisionado)

- **Novo**: `src/ml/models/erro_leitura_classifier.py`
  - **Weak supervision**: labels iniciais = `Causa Raiz` do CE + pseudo-labels dos tópicos BERTopic
  - Baseline: **Logistic Regression multiclasse** sobre embeddings
  - Modelo final: **LightGBM multiclasse** sobre `[embeddings PCA-32 + features categóricas + temporais]`
  - Validação: **TimeSeriesSplit** sobre `DT. INGRESSO` (sem leakage)
  - Métricas: macro-F1, per-class recall, matriz de confusão
  - Calibração via `CalibratedClassifierCV`
  - MLflow registry: `erro_leitura_classifier`

### Fase 6 — Detecção de padrões anômalos espaço-temporais

- **Novo**: `src/ml/models/erro_leitura_anomaly.py`
  - Agregação diária por `(região, classe_erro)` → série temporal
  - **Isolation Forest** + **Z-score rolling** (reuso do padrão `src/ml/models/anomalia_*`)
  - Detecta: picos por bairro/rota, concentração por leiturista (quando extraível), sazonalidade atípica
  - Saída: `gold.hotspots_erro_leitura` com score de anomalia

### Fase 7 — API de inferência (FastAPI)

- **Novo router**: `src/api/routers/erro_leitura.py`
  - `POST /erros-leitura/classificar` → recebe texto livre, retorna `{classe, probabilidade, top3}`
  - `GET /erros-leitura/padroes?periodo=` → distribuição de tópicos
  - `GET /erros-leitura/hotspots?regiao=&dt_ini=&dt_fim=` → anomalias
  - `GET /erros-leitura/{ordem}` → classificação + explicação (top tokens via SHAP sobre LightGBM)
- Auth: reuso do middleware JWT existente

### Fase 8 — Dashboard Superset

- **Novo dashboard**: "Erros de Leitura — Inteligência Operacional"
  - Mapa de calor CE/SP por causa-raiz
  - Evolução temporal por tópico
  - Top-10 rotas/bairros com pico de erros
  - Drill-down: amostras de observação por classe
  - KPI: `% erros reincidentes na mesma INSTALACAO (90 dias)`

### Fase 9 — Orquestração

- **Novo DAG**: `airflow/dags/dag_erro_leitura.py`
  - `ingest_descricoes → silver_normalize → dbt_gold → embed_texts → [topic_model, anomaly_detect] → classifier_inference → export_to_api`
  - Schedule: diário (ingestão incremental) + retreino semanal (topic + classifier)

## Arquivos Críticos

| Arquivo | Ação |
|---|---|
| `src/ingestion/descricoes_enel_ingestor.py` | novo — estende `BaseIngestor` |
| `src/ingestion/configs/descricoes_enel.yaml` | novo — mapping CE/SP |
| `src/transformation/processors/erro_leitura_normalizer.py` | novo |
| `src/ml/features/text_embeddings.py` | novo — sentence-transformers |
| `src/ml/models/erro_leitura_topic_model.py` | novo — BERTopic |
| `src/ml/models/erro_leitura_classifier.py` | novo — LightGBM + LR baseline |
| `src/ml/models/erro_leitura_anomaly.py` | novo — Isolation Forest |
| `src/api/routers/erro_leitura.py` | novo — endpoints FastAPI |
| `dbt/models/marts/erro_leitura/*.sql` | novos — fato + dims |
| `airflow/dags/dag_erro_leitura.py` | novo |
| `pyproject.toml` | editar — adicionar `sentence-transformers`, `bertopic`, `umap-learn`, `hdbscan` |
| `tests/unit/ingestion/test_descricoes_enel_ingestor.py` | novo |
| `tests/unit/ml/test_erro_leitura_classifier.py` | novo |
| `tests/integration/test_erro_leitura_pipeline.py` | novo — end-to-end |

## Reuso (não recriar)

- `BaseIngestor` (src/ingestion) — template method para leitura + metadata
- `BaseSilverTransformer` — dedup + reconciliação
- `BaseModelTrainer` (src/ml) — MLflow + sklearn pipelines
- `IODescriptor`, `RunManifest`, `SourceConfig` (src/common)
- Padrão de anomalia em `src/ml/models/anomalia_*`
- `dim_tempo` existente em dbt

## Restrições de Hardware (16GB / CPU-only)

- Embeddings: `batch_size=32`, modelo MiniLM (118MB), ~2k docs/min em i7-1185G7
- BERTopic: UMAP `n_neighbors=15, n_components=5`; HDBSCAN `min_cluster_size=20`
- LightGBM: `num_leaves=31, n_estimators=300`, sem GPU
- Dataset completo (~17k linhas) cabe em memória — usar **pandas/polars**
- Spark reservado para futuras ingestões incrementais de maior volume

## Verificação End-to-End

```bash
# 1. Ingestão
make dev
poetry run python -m src.ingestion.descricoes_enel_ingestor --input-dir DESCRICOES_ENEL/
# SELECT _source_region, COUNT(*) FROM bronze.descricoes_reclamacoes → CE e SP presentes

# 2. Silver + Gold
make pipeline
poetry run dbt run --select marts.erro_leitura
# Reconciliação: bronze_count == silver_count + rejected_count

# 3. ML
poetry run python -m src.ml.models.erro_leitura_topic_model --train
poetry run python -m src.ml.models.erro_leitura_classifier --train
# MLflow UI: macro-F1 ≥ 0.65 no holdout temporal

# 4. API
curl -X POST localhost:8000/erros-leitura/classificar \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"texto": "Cliente informa leitura estimada há 3 meses, medidor em local de difícil acesso"}'
# Esperado: {"classe": "acesso_negado", "probabilidade": 0.78, ...}

# 5. Testes
make test-unit
poetry run pytest tests/integration/test_erro_leitura_pipeline.py -v

# 6. Smoke
make smoke
```

## Definition of Done

- [ ] 12 arquivos Excel ingeridos em Bronze com auditoria (`_run_id`, contagem por região)
- [ ] Silver normalizado com schema unificado CE/SP, texto limpo, PII não vazada em logs
- [ ] Gold dimensional acessível via Trino; consultas respondem <2s
- [ ] BERTopic descobre ≥5 tópicos coerentes (revisão humana sobre amostra)
- [ ] Classificador com macro-F1 ≥ 0.65, calibrado, registrado no MLflow
- [ ] Anomalias detectadas com precisão validada manualmente em top-20
- [ ] API endpoints funcionais, autenticados, documentados em OpenAPI
- [ ] Dashboard Superset publicado com ≥4 gráficos
- [ ] DAG Airflow verde por 3 execuções consecutivas
- [ ] Cobertura de testes ≥80% nos módulos novos

---

## Extensão — Camada analítica CE Reclamações Totais (Abr/2026)

A guia `erro de leitura` representa apenas ~3% do volume CE (4,9k de 172,5k ordens). A guia `reclamacao_total` (167,6k) estava sub-aproveitada. Esta extensão entrega visão analítica completa sobre ela sem criar um modelo supervisionado adicional — o campo `assunto` (populado em >99%) já é a taxonomia autoritativa da ENEL.

### Decisão de design

Não treinar classificador supervisionado sobre `reclamacao_total`. Em vez disso:

1. **Taxonomia de negócio em 8 macro-temas** aplicada sobre `assunto` (normalizado upper), com regras ordenadas por precedência (primeiro match vence): Ouvidoria/Jurídico → GD → Religação/Multas → Entrega de Fatura → Média/Estimativa → Variação de Consumo → Refaturamento → Outros.
2. **Drill-down em `causa_raiz`** quando preenchida (cobre ~32% dos registros, majoritariamente ordens GA finalizadas).
3. **Agregações de BI/MIS** prontas para decisão: distribuição, Pareto 80/20, evolução mensal (MoM + MM3M), heatmap tema×mês, reincidência por instalação, radar GA vs GB, cruzamento com erros de leitura.

### Módulos entregues

| Arquivo | Papel |
|---|---|
| `src/viz/reclamacoes_ce_dashboard_data.py` | Data layer: `prepare_reclamacoes_ce_frame`, `compute_kpis`, `macro_tema_distribution`, `assunto_pareto`, `causa_raiz_drill`, `monthly_trend_by_tema`, `heatmap_tema_x_mes`, `top_instalacoes_reincidentes`, `radar_tema_por_grupo`, `cruzamento_com_erro_leitura`, `reincidence_matrix`, `executive_summary` |
| `apps/streamlit/erro_leitura_dashboard.py` | Nova aba **🟧 CE · Reclamacoes Totais** (6 seções: KPIs → resumo+distribuição → Pareto → evolução/heatmap → radar+drill → reincidência+cruzamento) |
| `tests/unit/viz/test_reclamacoes_ce_dashboard_data.py` | 12 testes cobrindo classificação, preparo, KPIs, agregações, radar, cruzamento e handling de frame vazio |

### Métricas observadas (dataset Silver atual)

- **Volume total**: 167.633 reclamações · 121 assuntos distintos · 15 meses (Jan/25–Mar/26)
- **Mix de macro-temas**: Refaturamento 54,9% · Religação/Multas 13,7% · GD 9,0% · Ouvidoria/Jurídico 8,2% · Variação Consumo 7,2% · Média/Estimativa 4,3% · Outros 1,8% · Entrega Fatura 0,9%
- **Pareto**: 10 assuntos concentram ~80% do volume
- **Grupo B**: 97,5% do volume · **Reincidência**: 23.241 instalações (17,6%) com ≥2 reclamações; 83 instalações com ≥10
- **Cobertura de `causa_raiz`**: 32% (label forte apenas parcial — por isso usada só em drill)

### Verificação

```bash
# Data layer
.venv/bin/python -m pytest tests/unit/viz/test_reclamacoes_ce_dashboard_data.py -q

# Dashboard local (requer Silver em data/silver/erro_leitura_normalizado.csv)
make dev
.venv/bin/streamlit run apps/streamlit/erro_leitura_dashboard.py
# Abrir aba "🟧 CE · Reclamacoes Totais"
```
