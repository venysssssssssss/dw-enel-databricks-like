# Sprint 25 — Recall Semântico e Calibração do Classificador `erro_leitura`

**Executor principal**: Claude Opus 4.7
**Modo esperado**: reasoning `high` para taxonomia + threshold; `medium` para implementação
**Período sugerido**: 1,5 semana (7 dias úteis com buffer)
**Precedência**: Sprint 17 (RAG · taxonomy v2), Sprint 24 (Severidade SP)
**Status**: `IMPLEMENTED` — automação verde em 2026-04-24; validação humana 200 linhas ainda pendente para cutover definitivo.
**Restrição dura**: nada de GPU, nada de transformer LLM em inferência. Tudo CPU em notebook 16 GB DDR4 / i7-1185G7.

---

## 1. Objetivo macro

Reduzir o uso da classe de fallback `indefinido` no classificador de erro de leitura — hoje em **44,26 %** do silver (46 % CE, 30 % SP) — para um patamar operacional que sustente as telas de Severidade (Sprint 24), o RAG (Sprint 17) e o MIS Executivo (Sprint 21) com sinal real, sem trocar o motor por um LLM transformer.

Resultado mensurável da sprint:

- `causa_canonica == 'indefinido'` cai para **≤ 25 % SP** e **≤ 35 % CE**.
- 4 novas classes canônicas adicionadas em `taxonomy_metadata()`, cobrindo padrões hoje órfãos.
- Threshold do classificador recalibrado, com novo bucket `causa_canonica_confidence ∈ {high, low, indefinido}`.
- Macro-F1 em holdout humano (200 amostras estratificadas) ≥ 0,78.
- Latência de re-rotulagem de 100 k linhas ≤ 90 s em CPU 4c/8t.
- Painel de Severidade SP do Sprint 24 não regride (Δvolume Alta+Crítica ≤ 5 %).
- Pipeline 100 % CPU. Zero dependência nova de transformer em inferência.

A sprint não é "trocar de modelo". É **fechar lacunas semânticas reais** identificadas por análise de dados, mantendo o motor keyword + regex + BERTopic existente.

---

## 2. Contexto real do repositório

### 2.1 Estado atual do classificador

`src/ml/models/erro_leitura_classifier.py` define:

- `TAXONOMY` (linhas 40–340): 14 classes canônicas com `keywords`, `patterns`, `severidade ∈ {low, medium, high, critical}`, `peso_severidade`.
- `KeywordErroLeituraClassifier` (linhas 438–542): scoring por substring + regex + penalidades negativas.
- Threshold: `min_score=1.0`, `margin_ratio=1.05`. Acima → label vencedor; senão → `"indefinido"`.
- `taxonomy_metadata()` (linhas 677–691): exposto como source-of-truth para `data_plane`, RAG, dashboards e a Sprint 24.

`canonical_label()` (linhas 661–675) normaliza rótulos humanos via `CANONICAL_LABEL_MAP`. Quando o operador não preencheu `causa_raiz`, o classificador entra; quando entrou, é mapeado para uma classe oficial ou cai em `indefinido` se nenhuma bater.

### 2.2 Diagnóstico do `indefinido` (100 k linhas, abr/2026)

| Métrica | Valor |
|---|---|
| Total `indefinido` global | 44,26 % |
| `indefinido` no recorte CE | 46,23 % |
| `indefinido` no recorte SP | 29,99 % |
| Top classe atual (não-indefinido) | `refaturamento_corretivo` (≈ 11 %) |

Top tokens em texto rotulado `indefinido` (após casefold + strip de stopwords): `procedente`, `conforme`, `solicitado`, `valor`, `mes`, `kwh`, `causa`, `erro`, `leiturista`, `instalacao`, `refat`, `digita`, `email`, `telefone`, `inst`, `aten`.

Padrões frasais recorrentes (amostra real do silver):

- *"corrigir consumo ref mes 05 06 e 07 2025 98 kwh para cada mes fvpou - procedente - corrigido consumos das ref 202505 a 202507 conforme solicitado em ordem - faturas atualizadas para pgto."*
- *"solicito correcao de consumo da referencia 20 06 2025 para 24 kwh fvpou - procedente - corrigido consumo da ref 202506 conforme solicitado em ordem - fatura atualizada para pgto."*
- *"refat"*, *"conf ajuste"*, *"ajustado em ordem"*.

Esses padrões **não são causa raiz** — são linguagem de resolução / outcome / canal. Hoje caem em `indefinido` porque a taxonomia v2 não tem classes para eles.

### 2.3 Topics BERTopic descobertos e não dobrados

`data/model_registry/erro_leitura/topic_taxonomy.json` carrega 8 topics. Três deles (3 / 4 / 5) somam ~4,3 k linhas e contêm exclusivamente vocabulário de resolução (`ajuste_corrigido`, `corrigida_ficou`, `refaturamento_ajuste`). Topic 2 e 7 são canal de atendimento (`anexo`, `mail`, `telefone`). Esses topics ficaram fora do mapeamento canônico e contribuem para inflar `indefinido`.

### 2.4 Por que o threshold tem culpa

`min_score=1.0` exclui qualquer linha onde a melhor classe tenha exatamente 1 keyword peso 1.0. `margin_ratio=1.05` derruba empates marginais. A consequência é que sinal fraco-mas-único cai em `indefinido` no lugar de propagar com baixa confiança. A sprint expõe esse sinal como `confidence=low` em vez de descartá-lo.

### 2.5 Dependências downstream

A redução de `indefinido` atinge:

- `severity_heatmap`, `severity_*` (Sprint 24).
- Cards RAG em `src/rag/ingestion.py` (causa_canonica entra na metadata).
- KPIs `mis_executive_summary`, `mis_monthly_mis`.
- `taxonomy_reference` exposto em `/v1/aggregations/taxonomy_reference`.

Toda mudança vive em camadas paralelas até validação para evitar regressão.

---

## 3. Não-objetivos (escopo barrado)

- **Sem trocar o motor por LLM em inferência.** A taxonomia continua sendo keyword + regex + BERTopic mapping.
- **Sem novas classes de severidade `high` ou `critical`.** As 4 novas são `low` por design — refletem processo, não falha técnica.
- **Sem reescrever o silver pipeline.** v3 escreve em colunas paralelas até cutover.
- **Sem mudar o front da Sprint 24** — a única exposição da sprint na UI é o respeito ao filtro `confidence=high` quando a tela for conservadora.
- **Sem alterar a taxonomia v2** retroativamente para preservar comparações históricas.

---

## 4. Frentes de trabalho — item a item

### Frente A — Taxonomia v3: 4 novas classes canônicas

**Motivação.** Os clusters semânticos identificados como dominantes em `indefinido` precisam de classes. Não rotulá-los significa que metade do volume RAG e BI hoje é cega.

**Novas classes** — todas `severidade=low`, `peso_severidade=1.0`:

| Classe | Sinais (resumo) |
|---|---|
| `procedimento_administrativo` | "procedente conforme solicitado", "ajuste realizado em ordem", "fatura atualizada para pagamento", "refaturamento ok" |
| `ajuste_numerico_sem_causa` | regex `r"corrig\w+ consumo (da )?ref(erencia)? \d{6}"`, `r"ajustad\w+ \w+ consumo .* \d+\s*kwh"` (correção numérica sem indício de causa) |
| `texto_incompleto` | comprimento ≤ 25 chars; ≥ 60 % dos tokens em `{refat, digita, conf, inst, fvpou, aten}`; tokens truncados |
| `solicitacao_canal_atendimento` | "telefone", "email", "agente", "central", "sms", "whatsapp" sem keyword de outras classes |

**Justificativa de severidade `low`.** São sinais de processo, não de falha técnica. Empurrá-las para `high` ou `critical` regrediria o painel da Sprint 24 (Alta/Crítica passaria a contar tickets de "ajuste OK"). Manter `low` preserva a integridade da hierarquia.

**Source of truth.** Toda nova classe entra em `TAXONOMY` no mesmo formato das v2 (keywords ponderadas, patterns regex, severidade, descrição). `taxonomy_metadata()` continua sendo o ponto único de exposição.

**DoD da frente A.**

- [ ] 4 entradas adicionadas a `TAXONOMY` em `src/ml/models/erro_leitura_classifier.py`.
- [ ] `taxonomy_metadata()` retorna 18 classes (14 v2 + 4 v3).
- [ ] `taxonomy_reference` view do data plane reflete as novas linhas sem mudança de schema.
- [ ] mypy + ruff verde no módulo.

### Frente B — Calibração de threshold + bucket `confidence`

**Motivação.** Sinal fraco-mas-único hoje vira `indefinido` silenciosamente. Substituir por bucket auditável.

**Mudanças.**

1. `min_score`: `1.0 → 0.6`. Permite classificar texto com 1 keyword única peso 1.0.
2. `margin_ratio`: `1.05 → 1.02`. Reduz empates marginais derrubados por arredondamento.
3. Nova coluna **`causa_canonica_confidence ∈ {high, low, indefinido}`**:
   - `top ≥ 1.0` e `top ≥ second × 1.05` → `high`.
   - `0.6 ≤ top < 1.0` ou `1.02 ≤ top/second < 1.05` → `low`.
   - caso contrário → `indefinido` (label `causa_canonica = "indefinido"`).
4. `causa_canonica` continua sendo o label vencedor mesmo no bucket `low`. UI / RAG / Sprint 24 escolhem se filtram.

**Justificativa.** Em vez de mascarar, exponho. O painel Sprint 24 mantém comportamento conservador filtrando `confidence='high'` no `_filter_sp_severidade`.

**DoD.**

- [ ] Novo argumento `confidence_threshold` no construtor do classificador (default 0.6).
- [ ] Coluna `causa_canonica_confidence` propagada em `prepare_dashboard_frame`.
- [ ] `_filter_sp_severidade` aceita kwarg `min_confidence` (default `'high'`).

### Frente C — Pré-classificação por regex de "resolução pura"

**Motivação.** O bucket `procedimento_administrativo` é tão dominante (estimado 8–12 pp do indefinido) que merece short-circuit antes do scoring.

**Implementação.**

```python
RESOLUCAO_RE = re.compile(r"(procedente.*conforme|ajuste\s+(realizado|conclu)|fatura\s+(atualizada|corrigida)\s+para\s+pgto|refat\s+ok)", re.I)
CAUSA_HINT_RE = re.compile(r"(medidor|leiturista|estim|digit|impedim|titularid|gd\s+|tarif|consumo\s+(elev|atip))", re.I)

def _is_resolucao_pura(text: str) -> bool:
    return RESOLUCAO_RE.search(text) is not None and CAUSA_HINT_RE.search(text) is None
```

Se `_is_resolucao_pura(texto)` → label = `procedimento_administrativo`, `confidence = high`. Caso contrário, prossegue para scoring keyword.

**DoD.**

- [ ] Função `_is_resolucao_pura` testada com 5 casos positivos e 5 negativos.
- [ ] Latência adicional ≤ 8 ns/linha em benchmark com 100 k frases.

### Frente D — Reaproveitamento dos topics BERTopic

**Motivação.** Os 8 topics existentes não são consumidos pela classificação. Topics 3 / 4 / 5 e 2 / 7 mapeiam para classes novas; topics 0 / 1 reforçam `consumo_elevado_revisao`; topic 6 reforça `medidor_danificado`.

**Tabela de mapeamento** — gravada em `data/model_registry/erro_leitura/topic_to_canonical.csv`:

| topic_id | nome BERTopic | canonical_target | confidence |
|---|---|---|---|
| 0 | consumo_variacao_dias | `consumo_elevado_revisao` | low |
| 1 | consumo_dias_variacao | `consumo_elevado_revisao` | low |
| 2 | anexo_mail_mail_anexo | `solicitacao_canal_atendimento` | low |
| 3 | ajuste_leit_ajustada | `procedimento_administrativo` | low |
| 4 | corrigido_ajuste_corrigido_ajustado | `procedimento_administrativo` | low |
| 5 | ajuste_corrigida_ficou | `procedimento_administrativo` | low |
| 6 | medidor_relogio_loja | `medidor_danificado` | low |
| 7 | tecnico_telefone | `solicitacao_canal_atendimento` | low |

**Pipeline de aplicação.** Quando o keyword classifier devolve `causa_canonica='indefinido'` e o `topic_id` da linha existe na tabela, sobrescrevemos para o `canonical_target` com `confidence='low'`. Não substitui o classificador, é segunda camada — falha graciosamente se topic_id ausente.

**DoD.**

- [ ] CSV versionado.
- [ ] `prepare_dashboard_frame` aplica o merge.
- [ ] Teste cobrindo: linha com keyword forte ignora topic; linha indefinido com topic mapeado adota target.

### Frente E — Telemetria e meta de cobertura

**Motivação.** A sprint só fecha quando `indefinido_ratio` cai abaixo da meta. Precisamos da métrica observável.

- Métrica nova `enel_classifier_indefinido_ratio{regiao}` exposta no `/metrics` do FastAPI (calculada a partir do silver carregado em memória pelo `DataStore`).
- Painel Grafana `infra/config/grafana/dashboards/classifier-coverage.json`:
  - série temporal de `indefinido_ratio` por região;
  - top-10 tokens em `indefinido` (atualizado em batch diário, exposto via aggregation `classifier_indefinido_tokens`);
  - share de cada bucket de confiança.
- Alerta `infra/config/prometheus/alerts/classifier.yml`:
  - `ClassifierIndefinidoSpike`: `indefinido_ratio > 0.4` por 24 h.
  - `ClassifierLowConfidenceMajority`: `confidence='low'` > 35 % por 7 dias (sinaliza necessidade de novo passe v4).

**DoD.**

- [ ] Painel JSON commitado.
- [ ] Alerta carregado pelo Prometheus (já configurado a partir da Sprint 24).
- [ ] `docs/RUNBOOK.md` ganha seção "Classifier coverage" descrevendo ação em cada alerta.

### Frente F — Re-rotulagem do silver e backfill

**Motivação.** A v3 só vale se aplicada a dados existentes. Backfill incremental, não destrutivo.

- Script novo `scripts/relabel_erro_leitura.py`:
  - lê `data/silver/erro_leitura_normalizado.csv`;
  - executa classificador v3;
  - escreve `causa_canonica_v3` e `causa_canonica_confidence` lado a lado com a coluna v2;
  - aceita `--report` (gera `reports/relabel_v3.json` com cobertura) e `--benchmark` (mede latência).
- Validação humana de 200 linhas estratificadas (50 v2-indefinido / 50 v3-indefinido / 50 v2-high / 50 v3-high).
- Após validação, swap `causa_canonica = causa_canonica_v3` em uma migração `silver-v3` versionada (novo `dataset_hash`).

**Arquivos afetados.**

- `src/viz/erro_leitura_dashboard_data.py::prepare_dashboard_frame` — consumir `confidence`.
- `src/data_plane/views.py` — aceitar `confidence` como filtro opcional nas group_keys quando útil.
- `src/rag/ingestion.py` — `confidence` entra no metadado dos cards; cards `low` recebem score-down no rerank.

**DoD.**

- [ ] Script roda end-to-end em ≤ 90 s sobre o silver de 100 k+ linhas.
- [ ] `reports/relabel_v3.json` mostra cobertura por região e por classe.
- [ ] Validação humana documentada em `docs/business-rules/taxonomia-v3-validation.md`.

### Frente G — Testes

Arquivo novo `tests/unit/test_erro_leitura_classifier_v3.py` cobrindo:

1. As 4 novas classes têm pelo menos 3 exemplos rotulados corretamente cada.
2. Frase canônica `"procedente - corrigido conforme solicitado"` → `procedimento_administrativo`, **não** `refaturamento_corretivo`.
3. Texto `"refat"` → `texto_incompleto`, `confidence='high'`.
4. Single-keyword peso 1.0 (`"leitura confirmada"`) deixa de cair em `indefinido` com novo threshold (`confidence='low'`).
5. Tokens de canal isolados (`"contato via email"`) → `solicitacao_canal_atendimento`.
6. Texto técnico claro (`"medidor queimado"`) **não** muda de classe — guarda contra regressão.
7. Mapping topic → canonical funciona quando keyword falha.
8. `_filter_sp_severidade(min_confidence='high')` exclui linhas `confidence='low'`.

Cobertura mínima: 90 % no módulo `erro_leitura_classifier.py` e 85 % no merge BERTopic.

**DoD.**

- [ ] `pytest tests/unit/test_erro_leitura_classifier_v3.py` 100 % verde.
- [ ] `pytest tests/unit/test_erro_leitura_ml.py` continua 100 % verde (sem regressão).

### Frente H — Documentação + handoff

- `docs/business-rules/taxonomia-v3.md` — diff vs v2, justificativa de cada nova classe, exemplos, tabela de severidade.
- `docs/business-rules/taxonomia-v3-validation.md` — protocolo da amostra estratificada de 200 linhas e resultado.
- `docs/api/aggregations.md` — adiciona coluna `causa_canonica_confidence` na descrição da família `sp_severidade_*` e em `category_breakdown`.
- `docs/RUNBOOK.md` — nova seção "Classifier coverage" com ação a tomar em cada alerta.
- Release notes deste documento (seção 12).

**DoD.**

- [ ] 2 docs de business-rules commitados.
- [ ] aggregations.md atualizado.
- [ ] RUNBOOK com playbook dos 2 novos alertas.

---

## 5. Plano de execução por dia

| Dia | Frentes | Saída |
|-----|---------|-------|
| 1 | A · Taxonomia v3 | 4 classes em `TAXONOMY`, descrição + keywords + patterns |
| 2 | B + C · threshold + resolução pura | classificador v3 funcionando local, smoke 1 k linhas |
| 3 | D · BERTopic mapping | CSV + merge no `prepare_dashboard_frame` |
| 4 | F · backfill | `scripts/relabel_erro_leitura.py` + report + benchmark |
| 5 | G · testes | suite v3 verde + sem regressão na suite v2 |
| 6 | E + H · observability + docs | painel Grafana + alertas + 2 docs |
| 7 | buffer | validação humana 200 linhas, ajustes finos, demo |

---

## 6. Critérios de aceite (executivos)

| Critério | Meta | Como medir |
|---|---|---|
| Indefinido SP | ≤ 25 % | `relabel_erro_leitura.py --report` |
| Indefinido CE | ≤ 35 % | mesmo report |
| Macro-F1 holdout (200 amostras humanas) | ≥ 0,78 | `test_erro_leitura_ml.py::test_classifier_training_returns_macro_f1` |
| Latência classificação 100 k linhas | ≤ 90 s em CPU 4c/8t | `--benchmark` no script |
| Pytest novo | 100 % verde | `pytest tests/unit/test_erro_leitura_classifier_v3.py` |
| Severidade SP painel não regride | volume Alta + Crítica varia ≤ 5 % | comparar `smoke_sp_severidade --all` antes/depois |
| Sem dependência GPU adicionada | confirmado | `pip-check` + diff `pyproject.toml` |

---

## 7. Riscos transversais e mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Novo threshold contamina painel Sprint 24 com `confidence=low` | Média | Médio | `_filter_sp_severidade(min_confidence='high')` por default |
| Classes `low` inflam volume "Médio/Baixo" do MIS | Alta | Baixo | Esperado por design; documentado em release notes |
| Re-label invalida embeddings RAG | Alta | Médio | `RAG_PROMPT_VERSION` bump → `make rag-rebuild`; já previsto no Makefile |
| BERTopic mapping fica desatualizado se houver retrain | Média | Baixo | CSV versionado; `make erro-leitura-train` emite warning de drift se topics novos não estiverem no CSV |
| Novas keywords colidem com classes v2 | Baixa | Médio | Testes de regressão em `test_erro_leitura_ml.py`; pre-classificação `_is_resolucao_pura` exige ausência de `CAUSA_HINT_RE` |
| Validação humana das 200 linhas atrasa cutover | Média | Médio | v3 escreve em colunas paralelas; cutover só ocorre após validação |

---

## 8. Pós-sprint (handoff Sprint 26 e 27)

- **Sprint 26** — RAG por ordem (já planejado): consumir `confidence` no rerank. Cards `low` recebem fator de penalização configurável.
- **Sprint 27** — Severidade CE (extensão da Sprint 24). Após v3, o ratio CE estará abaixo de 35 %, viabilizando paridade visual com SP.
- **Sprint 28** — Avaliação de embedding leve para "vizinho semântico" do `indefinido` residual (≤ 25 %), ainda CPU-only via `paraphrase-multilingual-MiniLM-L12-v2` que já existe para o RAG.

---

## 9. Anti-patterns barrados

- ❌ LLM transformer em inferência.
- ❌ Aumentar severidade das novas classes para inflar painel da Sprint 24.
- ❌ Esconder `indefinido` virando outra classe sem semântica (zero "outros catch-all" silencioso).
- ❌ Reescrever taxonomia v2 retroativamente — v3 sempre paralela até validação.
- ❌ Hard-coding de classe ou regra de confiança no front. Tudo passa por `taxonomy_metadata()` + classificador.
- ❌ Regenerar BERTopic do zero por motivo cosmético (custo de tempo + drift).
- ❌ Mexer no shape do `AggregationResponse` — confidence é coluna nova, não envelope novo.

---

## 10. Definition of Done — sprint inteira

- [ ] Frentes A–H concluídas e marcadas individualmente.
- [ ] Code review de no mínimo 1 par senior (data + back).
- [ ] Validação humana das 200 amostras documentada.
- [ ] Tag git `sprint-25-classifier-v3` criada.
- [ ] PR único squash-mergeado em `main` com título `feat(ml): classifier v3 — recall semântico · sprint 25`.
- [ ] Feature flag `classifier_v3` controla ativação no `DataStore` (default off em prod por 48 h).
- [ ] Painel Grafana ativo, alertas configurados, RUNBOOK atualizado.
- [ ] Release notes preenchidas no fim deste arquivo.

---

## 11. Apêndice — tabela de cobertura projetada

| Métrica | Hoje (v2) | Meta (v3) | Movimento |
|---|---|---|---|
| `indefinido` global | 44,3 % | ≤ 30 % | -14 pp |
| `indefinido` SP | 30,0 % | ≤ 25 % | -5 pp |
| `indefinido` CE | 46,2 % | ≤ 35 % | -11 pp |
| `confidence='high'` global | n/a | ≥ 60 % | novo |
| `confidence='low'` global | n/a | ≤ 15 % | novo |
| Macro-F1 holdout | ~0,72 | ≥ 0,78 | +6 pp |

Estimativas baseadas em: 8–12 pp ganho via `procedimento_administrativo` short-circuit; 4–6 pp via `texto_incompleto` + `solicitacao_canal_atendimento`; 3–5 pp via threshold relaxado; 2–3 pp via merge BERTopic.

---

## 12. Release notes (preencher no fechamento)

```text
- Adicionadas 4 classes canônicas v3: procedimento_administrativo,
  ajuste_numerico_sem_causa, texto_incompleto, solicitacao_canal_atendimento.
- Threshold do KeywordErroLeituraClassifier relaxado (min_score 1.0→0.6,
  margin_ratio 1.05→1.02) com bucket explícito causa_canonica_confidence.
- BERTopic topics 3/4/5/2/7 dobrados via topic_to_canonical.csv.
- scripts/relabel_erro_leitura.py: backfill paralelo (colunas v3) com
  --report e --benchmark.
- Painel Grafana classifier-coverage.json + 2 alertas Prometheus.
- _filter_sp_severidade aceita min_confidence (default 'high'),
  preservando comportamento da Sprint 24.
- docs/business-rules/taxonomia-v3.md + taxonomia-v3-validation.md.
- Validação automatizada: 289 testes unitários verdes; suíte estreita Sprint 25
  com 45 testes verdes; contratos API/scripts com 21 testes verdes.
- Lint dos arquivos tocados: verde.
- Lint global do repositório: ainda falha por dívida preexistente fora do escopo
  em Airflow, scripts legados, transformação e testes antigos.
- Cobertura indefinido e Macro-F1 holdout humano: pendentes de validação sobre
  silver completo e amostra humana estratificada.
```

## 13. Fechamento técnico executado

Status por frente:

| Frente | Status | Evidência |
|---|---|---|
| A — Taxonomia v3 | Concluída | `taxonomy_metadata()` expõe 18 classes; 4 classes novas testadas. |
| B — Threshold + confidence | Concluída | `KeywordErroLeituraClassifier` default `min_score=0.6`, `margin_ratio=1.02`; `causa_canonica_confidence` propagada. |
| C — Regex resolução pura | Concluída | `_is_resolucao_pura` e `_is_texto_incompleto` implementadas e testadas. |
| D — Topic mapping | Concluída | `data/model_registry/erro_leitura/topic_to_canonical.csv` versionado e aplicado no `prepare_dashboard_frame`. |
| E — Telemetria | Concluída | Views `classifier_coverage`, `classifier_indefinido_tokens`, gauge Prometheus e dashboard/alertas adicionados. |
| F — Backfill | Concluída | `scripts/relabel_erro_leitura.py` com `--report`, `--benchmark`, `--sample-size` e `--in-place`. |
| G — Testes | Concluída | `tests/unit/test_erro_leitura_classifier_v3.py` criado; unit suite completa verde. |
| H — Documentação | Concluída | `taxonomia-v3.md`, `taxonomia-v3-validation.md`, `aggregations.md` e `RUNBOOK.md` atualizados. |

Validações executadas:

```bash
poetry run pytest tests/unit/test_erro_leitura_classifier_v3.py tests/unit/test_erro_leitura_ml.py tests/unit/viz/test_erro_leitura_dashboard_data.py tests/unit/test_sp_severidade_views.py tests/unit/test_data_plane_store.py tests/unit/test_data_plane_views.py
# 45 passed

poetry run pytest tests/unit/test_data_plane_api.py tests/unit/test_api_app.py tests/unit/test_scripts.py
# 21 passed

poetry run pytest tests/unit
# 289 passed

poetry run ruff check src/ml/models/erro_leitura_classifier.py src/viz/erro_leitura_dashboard_data.py src/data_plane/store.py src/data_plane/views.py src/api/routers/dashboard.py scripts/relabel_erro_leitura.py tests/unit/test_erro_leitura_classifier_v3.py tests/unit/test_erro_leitura_ml.py tests/unit/viz/test_erro_leitura_dashboard_data.py tests/unit/test_sp_severidade_views.py tests/unit/test_data_plane_store.py tests/unit/test_data_plane_views.py
# All checks passed
```

Pendências não bloqueantes para cutover:

- Executar `scripts/relabel_erro_leitura.py --report --benchmark` no silver completo.
- Preencher o resultado real em `docs/business-rules/taxonomia-v3-validation.md`.
- Aprovar amostra humana estratificada de 200 linhas antes de sobrescrever coluna canônica produtiva.
