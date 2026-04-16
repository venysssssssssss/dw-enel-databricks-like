# Sprint 16 — React/TS Frontend + Rust Hot-Paths + Unified Data Plane

> **Executor**: GPT-5.4 (reasoning HIGH). Brief, dense, zero boilerplate. Cite exact files. Do not paraphrase.
> **Duração estimada**: 2 semanas.
> **Pré-requisitos**: Sprint 15 entregue (chat RAG + data cards no Streamlit).

---

## Context

A plataforma ENEL hoje serve BI/MIS/Storytelling **e** o chat RAG via Streamlit (`apps/streamlit/erro_leitura_dashboard.py`) com 9 abas. Dor atual:

1. **Streamlit** acopla render + estado + IO no mesmo processo Python → re-render full em cada interação, cache `st.cache_data` granularidade fraca, FCP > 1.5s.
2. **Hot paths em Python puro**: agregações do silver (184.690 linhas) em `src/viz/erro_leitura_dashboard_data.py`, BM25 lexical em `src/rag/retriever.py::lexical_overlap`, scoring híbrido, hashing embedder em `src/rag/ingestion.py`. Tudo single-thread Python — gargalo claro.
3. **Divergência de dados**: `src/rag/data_ingestion.py` gera *data cards* do silver para o RAG, mas as visões BI (`apps/streamlit/layers/{mis,executive,impact,patterns,taxonomy}.py`) consomem o mesmo silver via outro caminho (`load_dashboard_frame`). Risco de drift entre o que o usuário **vê** e o que o assistente **responde**.
4. **Cache**: `st.cache_data` por argumentos posicionais + assinatura de path (`path_fingerprint`). Sem invalidação cruzada, sem TTL, sem warmup, sem compartilhamento entre sessões.

**Outcome desejado**: SPA React/TS minimalista (paleta ENEL #870A3C/#C8102E/#E4002B já em `chat.py:54`), backend FastAPI servindo agregados versionados, Rust via PyO3 nos hot paths, **um único data plane** que alimenta BI e RAG simultaneamente, cache multi-camada (HTTP ETag + Redis + Rust LRU + Arrow IPC mmap).

---

## Arquitetura alvo

```
┌──────────────────────────────────────────────────────────────────┐
│ React 18 + Vite + TS  (apps/web/)                                │
│  - TanStack Query (cache HTTP, stale-while-revalidate)           │
│  - shadcn/ui + Tailwind  (paleta enel.tokens.ts)                 │
│  - Recharts/visx  (BI), react-markdown + SSE (chat)              │
│  - Zustand (UI state), URL state via tanstack/router             │
└────────────┬─────────────────────────────────────────────────────┘
             │ HTTP/SSE  (Bearer JWT, ETag, Brotli)
┌────────────▼─────────────────────────────────────────────────────┐
│ FastAPI gateway  (src/api/)                                      │
│  /v1/datasets/erro-leitura      → Arrow IPC stream               │
│  /v1/aggregations/{view}        → JSON cacheado por dataset_hash │
│  /v1/rag/stream                 → SSE token-a-token              │
│  /v1/rag/cards                  → cards versionados              │
└────────────┬─────────────────────────────────────────────────────┘
             │
   ┌─────────┴─────────┬──────────────────────┐
   ▼                   ▼                      ▼
┌─────────────┐   ┌──────────────────┐  ┌──────────────────────┐
│ Redis 7     │   │ enel_core (Rust) │  │ Data Plane Service   │
│ - JSON resp │   │ PyO3 module:     │  │ (src/data_plane/)    │
│ - rate lim. │   │ - aggregate()    │  │ - DatasetVersion     │
│ - SSE buf.  │   │ - bm25_score()   │  │ - feature_store      │
└─────────────┘   │ - hash_embed()   │  │ - cards_builder      │
                  │ - parquet→arrow  │  │   (compartilhado     │
                  │ - lru cache      │  │    BI ↔ RAG)         │
                  └──────────────────┘  └──────────────────────┘
                                              │
                                              ▼
                                   data/silver/*.parquet (Arrow mmap)
                                   data/rag/chromadb/
```

**Princípio único de dados**: `DatasetVersion` (hash sha256 do silver + topic_assignments + taxonomy) é a chave canônica de cache. **Toda** view BI e **todo** card RAG reescrevem-se em função desse hash. RAG não acessa CSV diretamente — vai ao mesmo `aggregate()` que alimenta o frontend.

---

## Escopo (8 entregas atômicas)

### E1 — Rust core via PyO3 (`rust/enel_core/`)

**Crate nova**, exposta como wheel `enel_core` (maturin). Workspace Cargo:

```
rust/enel_core/
  Cargo.toml             # pyo3 = "0.22", arrow = "53", polars = "0.43" (lazy), ahash, rayon
  src/lib.rs             # #[pymodule] enel_core
  src/aggregate.rs       # group_by + count/sum/refaturamento; usa polars LazyFrame
  src/bm25.rs            # BM25Okapi com k1=1.5 b=0.75; tokenizer unicode-segmentation
  src/hash_embed.rs      # MurmurHash3 → vetor f32 dim=384, normalizado L2
  src/cache.rs           # moka::sync::Cache<u64, Arc<Vec<u8>>> (LRU TTL=300s)
  src/parquet_io.rs      # leitura mmap (memmap2) + Arrow IPC
```

**API Python exposta** (substitui equivalentes Python; mantém assinaturas compatíveis):

| Símbolo Rust | Substitui |
|---|---|
| `enel_core.aggregate(parquet_path, group_keys, metrics) -> bytes` (Arrow IPC) | loop pandas em `src/viz/erro_leitura_dashboard_data.py::load_dashboard_frame` |
| `enel_core.bm25_score(query: str, docs: list[str]) -> list[float]` | `src/rag/retriever.py::lexical_overlap` |
| `enel_core.hash_embed(texts: list[str], dim: int = 384) -> np.ndarray` | `_load_embedder("hashing")` em `src/rag/ingestion.py` |
| `enel_core.parquet_to_arrow_ipc(path) -> bytes` | leituras CSV em loaders |

**Build**: `maturin develop --release` em CI; wheel em `dist/`. `pyproject.toml` adiciona `[project.optional-dependencies] core = ["enel_core==0.1.0"]` e fallback puro-Python preservado atrás de `try: import enel_core` (graceful degrade).

**Critério**: bench `pytest tests/perf/test_rust_speedup.py` mostra **≥10× speedup** em `aggregate` (160k linhas) e **≥30×** em `bm25_score` (1k passages). Memória pico ≤ 512MB.

---

### E2 — Data Plane unificado (`src/data_plane/`)

Novo módulo. **Substitui** acessos diretos ao CSV em layers Streamlit e em `src/rag/data_ingestion.py`.

```
src/data_plane/
  __init__.py
  versioning.py    # DatasetVersion(hash, sources, generated_at)
  store.py         # DataStore: load_silver(), aggregate(view), cards()
  views.py         # registro declarativo das views BI  (executive, mis, impact, patterns, taxonomy)
  cards.py         # MOVE de src/rag/data_ingestion.py — agora consome views.aggregate()
  cache.py         # camada Python sobre enel_core.cache + redis fallback
```

**Contrato**: cada view BI declara em `views.py` um `ViewSpec(id, group_keys, metrics, filters_schema)`. `DataStore.aggregate(view_id, filters)` é a **única** porta. Cards do RAG passam a chamar `store.aggregate("overview")`, `store.aggregate("by_region")` etc — eliminando duplicação de lógica entre `_overview_card`, `_top_assunto_card` (em `data_ingestion.py`) e os layers BI.

**Migração obrigatória** (deletar após swap, sem shims):
- `src/viz/erro_leitura_dashboard_data.py::load_dashboard_frame` → reduzido a thin wrapper que chama `DataStore.load_silver()` retornando pandas DataFrame.
- `src/rag/data_ingestion.py::build_data_cards` → reescrito chamando `store.cards()`.
- Layers `apps/streamlit/layers/{mis,executive,impact,patterns}.py` → cálculos pesados delegam a `store.aggregate()`.

**Critério**: `tests/integration/test_data_parity.py` executa todas as 9 views + 7 cards e confere bit-identidade (mesmo hash) entre o que BI mostra e o que o RAG ingere. Falha o build se divergir.

---

### E3 — FastAPI gateway (`src/api/routers/dashboard.py` + `rag.py`)

Endpoints novos (mantém estrutura `src/api/`):

| Método | Rota | Resposta |
|---|---|---|
| GET | `/v1/dataset/version` | `{hash, generated_at, sources[]}` — barata, usada para invalidação client |
| GET | `/v1/aggregations/{view_id}?filters=base64json` | JSON; header `ETag: dataset_hash:filters_hash`; `Cache-Control: max-age=60, stale-while-revalidate=300` |
| GET | `/v1/dataset/erro-leitura.arrow` | Arrow IPC stream (binário, brotli) — para casos onde frontend precisa do raw |
| GET | `/v1/rag/cards` | lista de cards (id, title, hash) |
| POST | `/v1/rag/stream` | SSE: `event: token \| meta \| citation \| done` |
| POST | `/v1/rag/feedback` | grava em `data/rag/feedback.csv` |

**Streaming RAG**: porta `_stream_answer` de `apps/streamlit/layers/chat.py` para `src/api/services/rag_stream.py`, removendo dependência de `st`. `RagOrchestrator` reusado intacto. SSE com `event:`/`data:` lines, heartbeat 15s.

**Cache server-side**: middleware Redis que chaveia por `(method, path, query, dataset_hash, role)`. TTL 300s. Invalidação por **publish** no canal `enel:dataset` quando `DatasetVersion` muda. ETag → 304 economiza payload.

**Critério**: p95 `/v1/aggregations/mis` ≤ 50ms cache hit, ≤ 250ms cache miss (com Rust). p95 first-token RAG ≤ 1.2s.

---

### E4 — React/TS SPA (`apps/web/`)

Stack imutável (não substituir):

```
vite + react 18 + typescript 5.5
@tanstack/react-query 5     # cache HTTP, stale-while-revalidate
@tanstack/react-router      # URL state (filtros persistidos)
zustand                     # UI state local (sidebar, theme)
tailwindcss + shadcn/ui     # design system
recharts                    # gráficos (BI)
react-markdown + remark-gfm # chat
@microsoft/fetch-event-source # SSE com retry/backoff
arrow-js                    # parsing Arrow IPC
```

**Estrutura**:

```
apps/web/
  src/
    app/
      routes/
        __root.tsx          # layout: sidebar + header + outlet
        index.tsx           # → /chat (default)
        chat.tsx            # tab 💬
        bi.mis.tsx          # tab 🧭
        bi.executive.tsx
        bi.patterns.tsx
        bi.impact.tsx
        bi.taxonomy.tsx
        bi.governance.tsx
        bi.educational.tsx
    components/
      chat/                 # ChatHero, MessageBubble, Citations, FeedbackRow
      bi/                   # KpiCard, TimeseriesChart, RegionMap, TopList
      shared/               # Sidebar, ThemeToggle, FilterChip, EmptyState
    lib/
      api.ts                # fetch wrapper, ETag store, retry
      sse.ts                # wrapper fetchEventSource
      query-keys.ts         # ['agg', view, filters, datasetHash]
      tokens.ts             # cores ENEL exatas de chat.py (#870A3C, #C8102E, #E4002B)
    hooks/
      useDatasetVersion.ts  # poll 30s, dispara invalidate
      useAggregation.ts     # useQuery key-aware
      useRagStream.ts       # SSE → state machine (idle|streaming|done|err)
    state/
      ui-store.ts           # zustand
```

**Cache policy** (TanStack Query):
- `staleTime`: 60s para agregações, 0 para `/dataset/version`.
- `gcTime`: 10min.
- `queryKey` inclui `datasetHash` ⇒ mudança de versão invalida tudo automaticamente.
- Persistência em `IndexedDB` via `@tanstack/query-sync-storage-persister` para warm-start cross-session.
- Service Worker (Workbox) com strategy `StaleWhileRevalidate` para `/v1/aggregations/*` e `CacheFirst` para `/v1/dataset/erro-leitura.arrow`.

**Design** (minimalista corporativo):
- Tipografia: Inter (UI), JetBrains Mono (números/códigos).
- Grid de 8px, raio 12, sombra `0 2px 6px rgba(0,0,0,0.04)`.
- Hero do chat reutiliza gradient `linear-gradient(135deg, #870A3C 0%, #C8102E 60%, #E4002B 100%)` (já em `chat.py:54`).
- Tema dark via `prefers-color-scheme` + override em URL `?theme=dark`.
- Acessibilidade: WCAG AA, foco visível, ARIA em chips/expanders, skip-link.

**Critério**: Lighthouse mobile ≥ 95 perf / ≥ 95 a11y / ≥ 100 best-practices. Bundle inicial gzipped ≤ 180KB. Tempo até interativo ≤ 1.5s em CPU 4× throttle.

---

### E5 — Cache multi-camada

| Camada | Onde | Chave | TTL | Invalidação |
|---|---|---|---|---|
| L0 — HTTP browser | Service Worker + TanStack Query | URL + datasetHash | 60s SWR | mudança datasetHash |
| L1 — CDN/ETag | resposta `ETag` | `dataset:filters` | infinito | `If-None-Match` → 304 |
| L2 — Redis | FastAPI middleware | `(view, filters, datasetHash)` | 300s | pub/sub `enel:dataset` |
| L3 — Rust LRU | `enel_core::cache` (moka) | `aggregate args hash` | 300s | reset on file change (notify) |
| L4 — Arrow IPC mmap | disco `data/silver/*.arrow` | path | persistente | rewrite on ingest |

**Invalidação central**: `src/data_plane/versioning.py::DatasetVersion.publish()` é o único caller que escreve em arquivos do silver. Ao terminar, publica no Redis e bumpa o hash. Tudo desce em cascata.

**Warmup** (`scripts/cache_warmup.py`): após qualquer rebuild, pré-popula L2/L3 com as 9 views × 4 filtros default. Roda em ~2s.

**Critério**: cache hit ratio ≥ 90% em sessão típica (script `tests/load/locust_session.py` com 50 usuários).

---

### E6 — Convergência RAG ↔ BI

**Pré-condição**: E2 entregue.

Mudanças:
1. `src/rag/data_ingestion.py` deletado (lógica migra para `src/data_plane/cards.py`).
2. `scripts/build_rag_corpus.py` agora chama `DataStore.cards()` — cards gerados a partir da **mesma** `aggregate()` que o frontend consome.
3. Cada `Chunk` ganha campo `dataset_version` no metadata Chroma. Retriever filtra por `dataset_version == current` evitando contexto stale.
4. Quando o frontend exibe um KPI ("184.690 ordens"), envia o `dataset_hash` no header `X-Dataset-Version` ao chamar `/v1/rag/stream`. Server valida match — se chat e UI estiverem em versões diferentes, força refresh.

**Critério**: `tests/integration/test_rag_bi_parity.py` para cada KPI da aba MIS, faz pergunta equivalente ao chat, parseia número da resposta, confere igualdade com o KPI. Tolerância 0.

---

### E7 — Observabilidade & qualidade

- Prometheus: métricas de cache hit/miss por camada, latência p50/p95/p99 por endpoint, tokens RAG por turno.
- Tracing: OpenTelemetry no FastAPI + propagação ao chat stream.
- Frontend: `web-vitals` reportando LCP/INP/CLS para `/v1/telemetry/web-vitals`.
- Testes: pytest (backend + Rust via `pyo3 + cargo test`), vitest + @testing-library/react (frontend), Playwright para E2E (`tests/e2e/`: chat, filtro persistente, invalidação de cache, SSE reconexão).

**Gate CI**: ruff + mypy + cargo clippy + cargo test + maturin build + vitest + playwright headless. Falha bloqueia merge.

---

### E8 — Decommission Streamlit (atrás de feature flag)

- `apps/streamlit/` mantido por 1 sprint em modo read-only (apenas `chat.py` redireciona para a SPA).
- Variável `ENEL_UI=react|streamlit` no nginx-proxy controla qual servir.
- Após validação (1 semana), remover `apps/streamlit/` inteiro + dependências `streamlit`, `streamlit-aggrid` do `pyproject.toml`. Sem shims.

---

## Arquivos críticos (modificar / criar)

**Criar**:
- `rust/enel_core/Cargo.toml`, `rust/enel_core/src/{lib,aggregate,bm25,hash_embed,cache,parquet_io}.rs`
- `src/data_plane/{__init__,versioning,store,views,cards,cache}.py`
- `src/api/routers/{dashboard,rag}.py`, `src/api/services/rag_stream.py`
- `apps/web/` (estrutura completa acima)
- `infra/dockerfiles/{web.Dockerfile,rust-builder.Dockerfile}`
- `infra/nginx/enel.conf` (proxy + brotli + cache)
- `scripts/cache_warmup.py`
- `tests/integration/test_data_parity.py`, `tests/integration/test_rag_bi_parity.py`, `tests/perf/test_rust_speedup.py`, `tests/e2e/*.spec.ts`

**Modificar (cirurgicamente, sem tocar lógica não relacionada)**:
- `src/rag/retriever.py` — `lexical_overlap` chama `enel_core.bm25_score` quando disponível.
- `src/rag/ingestion.py` — `_load_embedder("hashing")` delega a `enel_core.hash_embed`.
- `src/rag/data_ingestion.py` — deletar; lógica vai para `src/data_plane/cards.py`.
- `src/viz/erro_leitura_dashboard_data.py::load_dashboard_frame` — wrapper de `DataStore`.
- `apps/streamlit/erro_leitura_dashboard.py` — redireciona para SPA quando `ENEL_UI=react`.
- `pyproject.toml` — adiciona `enel_core`, `redis`, `httpx-sse`; remove `streamlit*` em E8.
- `infra/docker-compose.share.yml` — adiciona serviços `web`, `redis`, ajusta `streamlit` (deprecation).

---

## Verificação end-to-end

```bash
# Build Rust + wheel
cd rust/enel_core && maturin develop --release && cd -

# Backend
make pipeline                                           # gera silver + cards via data_plane
uvicorn src.api.main:app --reload                       # FastAPI
python scripts/cache_warmup.py                          # popula L2/L3

# Frontend
cd apps/web && pnpm install && pnpm dev                 # Vite em :5173

# Testes (todos devem passar; sem skips)
pytest tests/perf/test_rust_speedup.py -v               # ≥10× / ≥30× speedup
pytest tests/integration/test_data_parity.py -v         # BI == cards RAG
pytest tests/integration/test_rag_bi_parity.py -v       # KPIs == respostas chat
cd apps/web && pnpm test && pnpm test:e2e               # vitest + playwright
locust -f tests/load/locust_session.py --headless -u 50 -r 5 -t 1m  # cache hit ≥ 90%

# Lighthouse + bundle
pnpm build && pnpm lighthouse:ci                        # ≥95/95/100, bundle ≤180KB

# Observabilidade
curl :8000/metrics | grep enel_cache_                   # métricas por camada
```

**Definition of Done**: todas as métricas dos critérios cumpridas, gate CI verde, parity tests verdes, demo de uma sessão real (filtro → BI → pergunta no chat citando o KPI exibido) sem refresh manual.

---

## Status de implementação

**Entregue no repositório**

- E1 Rust core: crate `rust/enel_core` criada com PyO3 para `bm25_score`, `hash_embed`, cache LRU, `aggregate` e `parquet_to_arrow_ipc`, com fallback Python preservado em `src/rag/retriever.py` e `src/rag/ingestion.py`.
- E2 Data Plane: `src/data_plane/` centraliza versão de dataset, views declarativas, agregações e cards RAG.
- E3 FastAPI: rotas `/v1/dataset/version`, `/v1/aggregations/{view_id}`, `/v1/dataset/erro-leitura.arrow`, `/v1/rag/cards`, `/v1/rag/stream`, `/v1/rag/feedback` e `/v1/telemetry/web-vitals`.
- E4 React/TS SPA: `apps/web/` com Vite, React Query, TanStack Router, Zustand, Recharts, Markdown, SSE e Playwright smoke.
- E5 Cache: ETag/304, cache de resposta em memória com TTL, warmup via `scripts/cache_warmup.py` e métricas Prometheus `enel_cache_events_total`.
- E6 Convergência RAG ↔ BI: cards são gerados por `DataStore.cards()`, chunks carregam `dataset_version`, retriever aceita filtro de versão e `/v1/rag/stream` rejeita cliente stale.
- E7 Observabilidade & qualidade: Prometheus FastAPI existente, métricas de cache/web-vitals, testes Python de paridade, Vitest e Playwright.
- E8 Streamlit feature flag: `ENEL_UI=react` redireciona para SPA; compose share mantém Streamlit em modo legado e serve React por padrão.

**Validação executada nesta entrega**

- `pytest tests/unit -q`
- `pytest tests/integration/test_data_parity.py tests/integration/test_rag_bi_parity.py tests/perf/test_rust_speedup.py -q`
- `pnpm --dir apps/web test`
- `pnpm --dir apps/web build`
- `pnpm --dir apps/web test:e2e`

**Limitação local**

- `cargo test --manifest-path rust/enel_core/Cargo.toml` não pôde ser executado neste host porque `cargo` não está instalado. O Dockerfile `infra/dockerfiles/rust-builder.Dockerfile` documenta o caminho reprodutível para build com `maturin`.
