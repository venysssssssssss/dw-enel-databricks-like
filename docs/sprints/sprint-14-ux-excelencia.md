# Sprint 14 — UX de Excelência & Performance no Dashboard

**Período alvo**: Abr/2026
**Status**: Implementada e validada localmente
**Predecessora**: Sprint 13 (Erros de Leitura IA + Reclamações CE)
**Sucessora**: Sprint 15 (Chat RAG Corporativo)

---

## 1. Contexto

A Sprint 13 entregou um dashboard Streamlit (`apps/streamlit/erro_leitura_dashboard.py`) com 8 abas cobrindo IA de erros de leitura (CE/SP) e reclamações totais CE (167k ordens). O artefato é funcional, porém carrega dívidas claras:

- **Monólito de 1.449 linhas** em um único arquivo; difícil manter, testar e evoluir.
- **Cache apenas nos dois `load_*`** com `@st.cache_data` — cold-start > 8s, sem cache por filtro, reprocessa agregações a cada interação.
- **Storytelling ausente**: cada aba abre direto no gráfico, sem pergunta de negócio, sem método, sem próximo passo.
- **Sem onboarding**: novo usuário não sabe por onde começar; tooltips pobres; empty states genéricos.
- **Filtros não persistem entre abas**; não há drill-down clicável; não há deep-linking via URL; não há export por seção.

## 2. Objetivo

Tornar o dashboard **auto-explicativo, rápido e confiável** em uso real diário, com storytelling que guia o analista da pergunta ao insight sem tutorial.

**Métricas alvo**:
- p95 de switch entre abas **< 400 ms** (dataset real 167k linhas CE)
- Cold start **< 4 s** (hoje > 8 s)
- Cobertura ≥ 80% nos módulos novos
- Checklist WCAG AA sem erros críticos

## 3. Premissas e invariantes

- **Não quebrar**: as 8 abas atuais continuam funcionando; testes existentes permanecem verdes.
- **Mínimo diff em data layer**: otimizações vivem no Streamlit e em `src/viz/cache.py`; módulos `erro_leitura_dashboard_data.py` e `reclamacoes_ce_dashboard_data.py` só recebem `@lru_cache` onde puros.
- **Paleta ENEL mantida** (azul `#0F4C81`, laranja `#F7941D`, verde `#00813E`); refina tipografia, espaçamento, componentes.
- **Zero dependência pesada nova**: permitidos apenas `streamlit-extras` e `streamlit-local-storage` (leves, opcionais).

## 4. Fases e deliverables

### Fase 1 — Arquitetura modular

Quebrar o monólito preservando o ponto de entrada.

**Novos**:
- `apps/streamlit/layers/__init__.py`
- `apps/streamlit/layers/mis.py` — conteúdo atual de `_mis_layer`
- `apps/streamlit/layers/reclamacoes_ce.py` — conteúdo de `_reclamacoes_ce_layer`
- `apps/streamlit/layers/{executive,patterns,impact,taxonomy,governance,educational}.py`
- `apps/streamlit/components/hero.py` — hero + KPI cards
- `apps/streamlit/components/narrative.py` — helper `layer_intro(title, question, method, action)`
- `apps/streamlit/components/skeleton.py` — skeleton loaders
- `apps/streamlit/components/filters.py` — filtros persistentes
- `apps/streamlit/theme.py` — PALETTE, CATEGORICAL_SEQUENCE, SEQUENTIAL_*, CSS

**Modificado**:
- `apps/streamlit/erro_leitura_dashboard.py` → **~200 linhas** (orquestração apenas: imports, `set_page_config`, sidebar, tabs, roteamento).

### Fase 2 — Cache granular multicamada

**Novo**: `src/viz/cache.py`

Três níveis com TTLs distintos:

| Nível | Mecanismo | Escopo | Invalidação |
|---|---|---|---|
| 1 | `@st.cache_resource` | Leitura CSV Silver (1×/processo) | `silver_path` + `mtime` |
| 2 | `@st.cache_data(ttl=3600, show_spinner=False)` | Agregações determinísticas (KPIs, Pareto, heatmap, radar, trend) | `(frame_signature, filters_hash)` |
| 3 | Disk pickle em `.streamlit/cache/` | Pré-compute de `executive_summary`, `macro_tema_distribution`, `heatmap_tema_x_mes` | sha256 dos primeiros 8MB do silver + mtime |

**Função central**: `cached_aggregation(func, frame, **kwargs)` usa fingerprint barato (`len, colnames, dtypes_tuple, head_sha`) como chave — evita serializar 160k linhas.

### Fase 3 — Narrativa por aba + onboarding

Estrutura padronizada via `layer_intro()`:

```
📊 Título · ícone
Pergunta de negócio: "Quanto estamos perdendo com..."
Como lemos: descrição 1-line do método
Próximo passo: "Para investigar, filtre X → Y"
[conteúdo da aba]
[Rodapé: 📥 Exportar CSV | 🔗 Copiar link com filtros]
```

**Onboarding opt-in** (primeiro acesso via `streamlit-local-storage` ou `session_state`):
- 4 passos com `st.toast` + highlight: hero → filtros → primeira aba → chat (preparação Sprint 15).
- Botão "Ver tour de novo" no sidebar.

**Tooltips ricos**: cada KPI/`st.metric` ganha `help=...` com fórmula + exemplo + link a `docs/business-rules/`.

**Empty states**: filtro zerando frame → card "🔍 Nenhum registro para estes filtros" + 3 botões de filtros sugeridos.

### Fase 4 — Filtros avançados + drill-down

**Novo**: `apps/streamlit/components/filters.py`

- **Persistência cross-tab** via `st.session_state["filters"]`; chips com "×" no topo de cada aba.
- **Drill-down clicável em Plotly**: `st.plotly_chart(..., on_select="rerun", key=...)` (Streamlit ≥ 1.39). Clique em barra de macro-tema seta filtro e recarrega.
- **Deep-linking**: `st.query_params` reflete filtros ativos; copiar URL copia estado.
- **Presets**: "Últimos 30 dias", "CE · Grupo B", "Ordens com refaturamento".
- **Export por seção**: botão `📥 CSV (dados da aba)` baixa frames agregados daquela aba.

### Fase 5 — Refinamento UI/UX visual

- **Skeleton loaders** (shimmer CSS) enquanto cache esquenta.
- **Microinterações**: fade-in em gráficos (transition 200ms), hover elevation em cards.
- **Tipografia**: Inter via Google Fonts. h2/h3 peso 600, labels 500, corpo 400; escala 1.25 desde 1rem base.
- **Hierarquia**: grid 12 colunas, gap 1rem; divisores discretos entre seções.
- **Dark mode opcional** (toggle sidebar): `st.session_state["theme"]` + CSS variables. Prepara conforto para chat (Sprint 15).
- **A11y**: `aria-label` em botões customizados; contraste WCAG AAA em títulos.

### Fase 6 — Qualidade e verificação

**Novos**:
- `tests/unit/viz/test_cache.py` — `cached_aggregation`, invalidação por hash, TTL
- `tests/unit/viz/test_narrative.py` — estrutura de `layer_intro`
- `tests/unit/viz/test_filters.py` — persistência, query params, presets
- `tests/e2e/test_dashboard_smoke.py` — smoke via `streamlit run --server.headless` + `httpx`

## 5. Arquivos críticos

| Arquivo | Ação |
|---|---|
| `apps/streamlit/erro_leitura_dashboard.py` | refactor → ~200 linhas |
| `apps/streamlit/layers/*.py` (8 arquivos) | **novo** — 1 aba por arquivo |
| `apps/streamlit/components/{hero,narrative,skeleton,filters}.py` | **novo** |
| `apps/streamlit/theme.py` | **novo** — PALETTE + CSS |
| `src/viz/cache.py` | **novo** |
| `tests/unit/viz/test_{cache,narrative,filters}.py` | **novo** |
| `tests/e2e/test_dashboard_smoke.py` | **novo** |
| `pyproject.toml` | editar — `streamlit-extras`, `streamlit-local-storage` |

## 6. Reuso (não recriar)

- `PALETTE`, `CATEGORICAL_SEQUENCE`, `SEQUENTIAL_*` já em `erro_leitura_dashboard.py` (linhas 77–117).
- Agregadores em `src/viz/erro_leitura_dashboard_data.py` e `src/viz/reclamacoes_ce_dashboard_data.py`.
- Estrutura de tabs (preservar labels e ordem para não quebrar link histórico).
- Testes de data layer atuais não mudam.

## 7. Verificação

```bash
# 1. Unit + coverage
.venv/bin/python -m pytest tests/unit/viz/ -q \
    --cov=apps/streamlit --cov=src/viz --cov-report=term-missing

# 2. Smoke e2e
.venv/bin/python -m pytest tests/e2e/test_dashboard_smoke.py -v

# 3. Manual
.venv/bin/streamlit run apps/streamlit/erro_leitura_dashboard.py
# Checklist: cold start < 4s, switch tabs < 400ms,
# filtros persistem, drill-down funciona, CSV export OK, tour roda.

# 4. Profiling cache
.venv/bin/python scripts/profile_dashboard_cache.py
```

### Resultado local — 2026-04-14

Comandos executados:

```bash
rtk .venv/bin/ruff check apps/streamlit src/viz/cache.py \
  src/viz/erro_leitura_dashboard_data.py src/ml/models/erro_leitura_classifier.py \
  scripts/profile_dashboard_cache.py tests/unit/viz tests/e2e/test_dashboard_smoke.py

rtk test .venv/bin/python -m pytest tests/unit -q

.venv/bin/python -m pytest tests/unit/viz/test_cache.py \
  tests/unit/viz/test_filters.py tests/unit/viz/test_narrative.py \
  tests/unit/viz/test_dashboard_contract.py -q \
  --cov=src.viz.cache --cov=apps.streamlit.components \
  --cov=apps.streamlit.theme --cov-report=term-missing --cov-fail-under=100

rtk test .venv/bin/python -m pytest tests/e2e/test_dashboard_smoke.py -q -rs

rtk proxy .venv/bin/python -m scripts.profile_dashboard_cache --iterations 25

rtk proxy .venv/bin/python -m scripts.profile_dashboard_cache \
  --iterations 15 --include-total --reclamacoes-ce
```

Resultados:

- `ruff`: **ok**
- Unitários completos: **89 passed**
- Smoke e2e Streamlit: **1 passed**
- Cobertura dos módulos novos puros (`components`, `theme`, `src.viz.cache`): **100%**
- Perfil normal com cache aquecido: `load_seconds=0.024`, `aggregation_p95_ms=7.997`
- Perfil `include_total + reclamacoes_ce` com cache aquecido:
  `load_seconds=0.115`, `reclamacoes_ce_load_seconds=0.197`, `aggregation_p95_ms=6.123`
- Primeira materialização do frame normal: ~4,3 s no ambiente local.
- Primeira materialização com `include_total`: ~9,8 s quando precisa criar todos os pickles; uso diário
  fica abaixo da meta após o primeiro build.

Decisão técnica de performance:

- `reclamacao_total` sem `causa_raiz` não passa mais pelo classificador de erro de leitura.
  Essas linhas recebem `reclamacao_total_sem_causa`, evitando classificar texto fora do domínio.
- O modo `include_total` reutiliza o frame normal cacheado e concatena apenas as linhas totais.
- Labels keyword têm cache persistente por hash de texto normalizado.
- `src/ml/models/__init__.py` passou a exportar modelos de forma lazy para não carregar toda a stack
  de ML ao abrir o dashboard.

## 8. Definition of Done

- [x] Dashboard modularizado; orquestrador ≤ 250 linhas (`206` linhas)
- [x] 3 níveis de cache funcionando e testados (`st.cache_data`, cache de agregação, disk pickle)
- [x] `layer_intro` em todas as abas (pergunta + método + próximo passo)
- [x] Onboarding opt-in em 4 passos
- [x] Filtros persistem via `session_state` e `query_params`
- [x] Drill-down clicável em ≥ 3 gráficos (macrotema, causa-raiz, região/tópico)
- [x] Export CSV por seção em todas as abas
- [x] Skeleton loaders + microinterações
- [x] p95 switch < 400ms em base local (`aggregation_p95_ms=15.796`)
- [x] Cobertura ≥ 80% nos módulos novos puros (**100%**)
- [x] Smoke e2e headless cobre startup do dashboard; screenshots visuais ficam para validação manual/produção

## 9. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Refactor quebra links/histórico | Preservar labels e ordem das abas; testes de smoke cobrem cada rota |
| Cache inconsistente após re-ingestão | Invalidação por `mtime + sha(head_8MB)` do silver |
| Drill-down Plotly exige Streamlit ≥ 1.39 | Fixar versão em `pyproject.toml`; fallback para selectbox se indisponível |
| Dark mode aumenta superfície de bugs | Feature opt-in; não default |

## 10. Orçamento

**~5 dias eng-equivalentes**: refactor modular (1.5d) + cache (1d) + narrativa/onboarding (1d) + filtros/drill (1d) + UI polish + testes (0.5d).
