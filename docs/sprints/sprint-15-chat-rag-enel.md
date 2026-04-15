# Sprint 15 — Chat RAG Corporativo Embarcado no Dashboard

**Período alvo**: Abr–Mai/2026
**Status**: Planejada
**Predecessora**: Sprint 14 (UX de excelência — pré-requisito para tema, cache e componentes)
**Sucessora**: —

---

## 1. Contexto

Analistas ENEL não têm como perguntar em linguagem natural sobre a plataforma:

- _"Por que o refaturamento subiu em junho?"_
- _"O que é ACF/ASF?"_
- _"Como o modelo de erro de leitura classifica acesso impedido?"_

O conhecimento existe — **~50k tokens em 39 arquivos** de `docs/` (sprints, business-rules, architecture, ml, api, viz, runbook) + docstrings de código — mas está fragmentado. A Sprint 15 entrega um chat conversacional dentro do Streamlit que responde com **citações auditáveis**, **economia agressiva de tokens** e UX padrão ENEL.

## 2. Objetivo

Chat RAG de alta qualidade dentro do dashboard, com perguntas pré-existentes, saudação contextualizada, streaming, abstração multi-provider e custo controlado.

**Métricas alvo**:
- First-token **< 1.5 s** em cache hit, **< 4 s** cold
- Accuracy no eval-gabarito **≥ 80%**, citation rate **≥ 95%**
- Custo médio por turno **≤ $0.005 USD** em Haiku/mini
- Prompt cache hit rate **≥ 60%** em conversa de 6 turnos
- Budget médio **≤ 3k tokens/turno**; hard limit 8k

## 3. Premissas e restrições (alinhado com usuário)

- **Provedor**: multi-provider (OpenAI + Anthropic + Ollama) selecionado por `.env`. Default: **Anthropic Claude** (reasoning + prompt caching nativo).
- **Vector store**: **ChromaDB embarcado** (SQLite-backed, metadata filtering).
- **Embeddings**: híbrido — **MiniLM PT-BR** (`paraphrase-multilingual-MiniLM-L12-v2`, já usado via `TextEmbeddingBuilder`) para top-K local, **rerank** dos top-5 via LLM barato (haiku/mini).
- **Performance**: streaming obrigatório.
- **Paleta ENEL**: painel lateral (drawer) + aba dedicada, consistente com Sprint 14.

## 4. Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│ Streamlit Dashboard (Sprint 14)                              │
│ ┌──────────┐  ┌─────────────────────────────────────────┐   │
│ │ 8 abas   │  │ 💬 Chat RAG ENEL (nova aba + drawer)    │   │
│ └──────────┘  └────┬─────────────────────────────────────┘   │
│                    ▼                                         │
│          ┌──────────────────────────┐                        │
│          │ src/rag/orchestrator.py  │                        │
│          └──┬────────┬─────────┬────┘                        │
│       ┌─────▼──┐ ┌──▼────┐ ┌──▼──────────┐                  │
│       │Retriev │ │Rerank │ │LLM Gateway  │                  │
│       │ (Chr.) │ │ (LLM) │ │multiprovider│                  │
│       └─────┬──┘ └───────┘ └─────────────┘                  │
│             ▼                                                │
│       ChromaDB ./data/rag/ · collection: enel_docs           │
└──────────────────────────────────────────────────────────────┘

Ingestão (offline):
  docs/**/*.md + CLAUDE.md + README.md + src/**/*.py (docstrings)
    → chunker (MarkdownHeader + RecursiveChar, ~600 tokens, overlap 80)
    → MiniLM PT-BR (384d)
    → ChromaDB persist (./data/rag/chromadb/)
```

## 5. Fases e deliverables

### Fase 1 — Fundamentos e config

**Novos**:
- `src/rag/__init__.py`
- `src/rag/config.py` — `RagConfig` (pydantic) lê `.env`: `RAG_PROVIDER`, `RAG_MODEL`, `RAG_API_KEY`, `RAG_EMBEDDING_MODEL`, `RAG_CHROMADB_PATH`, `RAG_MAX_TURN_TOKENS`, `RAG_RERANK_ENABLED`, `RAG_STREAM`.
- `src/common/llm_gateway.py` — interface `LLMProvider` (`complete(messages, stream, cache_control)`) + adapters `AnthropicProvider`, `OpenAIProvider`, `OllamaProvider`.

**Editar**:
- `.env.example` — seção `# RAG chat`.
- `pyproject.toml` — extra `rag = ["anthropic>=0.39", "openai>=1.50", "chromadb>=0.5", "tiktoken>=0.7", "httpx>=0.27"]`.

### Fase 2 — Ingestão do corpus

**Novos**:
- `src/rag/ingestion.py` — `build_corpus(root_paths, output_path)`:
  - Descobre: `docs/**/*.md`, `README.md`, `CLAUDE.md`, `airflow/dags/*.py` (docstrings), `src/**/__init__.py`, `apps/streamlit/**/*.py`.
  - Extrai metadata: `{title, path, section, sprint_id, doc_type, token_count, created_at}`.
  - Chunker 2 estágios: `MarkdownHeaderSplitter` → `RecursiveCharacterSplitter` (`chunk_size=600 tokens`, `overlap=80`). `tiktoken` (cl100k_base) para contagem precisa.
  - Embedda via `TextEmbeddingBuilder` existente (reuso).
  - Persiste em ChromaDB.
- `scripts/build_rag_corpus.py` — CLI: `--rebuild` + estatísticas.
- `tests/unit/rag/test_ingestion.py` — chunker, tamanhos, overlap, metadata.

**Alvo**: 39 arquivos → ~200–300 chunks, ~50k tokens indexados.

### Fase 3 — Retrieval híbrido

**Novos**:
- `src/rag/retriever.py`:
  - `HybridRetriever(chroma_path, embedder)`:
    - `retrieve(query, k=20, filters=None)` — top-20 cosine; filtros por `doc_type`.
    - `rerank(query, candidates, llm, top_n=5)` — prompt curto, retorna JSON ranqueado; usa provider barato via `RAG_RERANK_MODEL`.
  - **Roteamento heurístico**: termos técnicos (ACF, ASF, refaturamento, GD) aplicam filtro `doc_type` antes do retrieval — reduz ruído e tokens.
- `tests/unit/rag/test_retriever.py` — mocka ChromaDB + LLM; testa fluxo, fallback, filtros.

### Fase 4 — Orquestrador + otimização de tokens

**Novos**:
- `src/rag/orchestrator.py` — `RagOrchestrator(retriever, gateway, config)`, `answer(question, history)`:

  **Pipeline**:
  1. **Intent classifier leve** (regex + keyword) → `{saudacao, glossario, dashboard_howto, analise_dados, dev, out_of_scope}`. Pula retrieval em saudação/out-of-scope.
  2. **History compactation** — `len(history) > 6` sumariza turnos antigos em 1 bullet via LLM barato (cached). Mantém últimos 4 íntegros.
  3. **Retrieval** → top-20 → rerank → top-5.
  4. **Prompt assembly com caching**:
     - **Estático cacheado** (~800t, `cache_control: ephemeral`): sistema + taxonomia + regras de citação. Economia ~70% multi-turno.
     - **Semicacheado** (~1800t): top-5 passages, cacheável 5 min se query similar.
     - **Dinâmico** (~400t): pergunta + histórico compacto.
  5. **Streaming** via `st.write_stream`.
  6. **Citações** `[fonte: docs/business-rules/glossario.md#acf-asf]` convertidas em links clicáveis por regex pós-proc.

  **Budget por turno**: `RAG_MAX_TURN_TOKENS=3000`. Excedeu? reduz rerank K→3, trunca passagens longas (preserva início + summary via LLM). Soft limit com warning no UI.

- `src/rag/prompts.py` — templates PT-BR versionados, separação estático/dinâmico.
- `tests/unit/rag/test_orchestrator.py` — mocks; testa pipeline, budget, compactação, out-of-scope.

### Fase 5 — UI do chat

**Novos**:
- `apps/streamlit/layers/chat.py` — aba "💬 Assistente ENEL" (primeira posição):
  - **Saudação inteligente**: hora do dia + último contexto do dashboard em `session_state["last_context"]` → _"Bom dia! Vi que você estava olhando refaturamento em CE. Quer entender os padrões do mês?"_
  - **Perguntas pré-existentes** (chips clicáveis), 8 curadas:

    | # | Pergunta | Intent |
    |---|---|---|
    | 1 | O que é ACF/ASF? | business |
    | 2 | Como o modelo de erro de leitura classifica? | ml |
    | 3 | Como interpretar o gráfico de radar? | dashboard |
    | 4 | Como rodar o pipeline localmente? | dev |
    | 5 | Por que o refaturamento está alto? | analise_dados |
    | 6 | Quais os KPIs da Sprint 13? | sprint |
    | 7 | Como funciona a ingestão Bronze? | architecture |
    | 8 | Mostre regras de PII | governance |

  - **UI**: `st.chat_message` com avatares ENEL, streaming via `st.write_stream`, citações como badges clicáveis (expander com trecho exato).
  - **Ações por resposta**: 👍 / 👎 (salva em `data/rag/feedback.csv`), 📋 copiar, 🔗 compartilhar (URL com query param).
  - **Estado**: `st.session_state["chat_history"]`; persiste via query_params curtos (hash).
  - **Indicadores**: badge do provider (🤖 Claude / GPT / Ollama), badge de tokens (verde < 2k, amarelo < 4k, vermelho > 4k), spinner no rerank.

- `apps/streamlit/components/chat_widget.py` — drawer lateral (`st.sidebar.expander` estilizado) que renderiza chat em miniatura em qualquer aba.

### Fase 6 — Observabilidade e governança

**Novos**:
- `src/rag/telemetry.py` — logger estruturado em `data/rag/telemetry.jsonl`:
  ```json
  {"ts":"...", "provider":"anthropic", "model":"claude-haiku-4-5",
   "question_hash":"...", "n_chunks":5, "prompt_tokens":2100,
   "completion_tokens":420, "cache_hit":true,
   "latency_first_token_ms":820, "latency_total_ms":3100,
   "intent_class":"analise_dados", "cost_usd_estimated":0.0042}
  ```
  Nunca loga texto completo (hash + 80 chars).

- `src/rag/safety.py`:
  - **Entrada**: rejeita padrões de prompt injection e PII óbvia (CPF, e-mail) — pede refrasear.
  - **Saída**: remove PII gerada (regex + lista de nomes).
  - **Out-of-scope**: se nenhum chunk > threshold 0.45, responde _"Não tenho essa informação nos documentos da plataforma"_ em vez de alucinar.

- `scripts/rag_eval.py` — 20 perguntas-gabarito em `tests/fixtures/rag_eval.yaml` (resposta esperada + citação obrigatória). CI falha se accuracy < 80% ou citation_rate < 95%.

### Fase 7 — Documentação

- `docs/sprints/sprint-15-chat-rag-enel.md` — este arquivo.
- `docs/rag/README.md` — guia rápido (trocar provider, reindexar, adicionar pergunta pré-existente).
- `docs/rag/prompt-design.md` — racional dos blocos cacheados, economia esperada, novo intent.

## 6. Otimização de tokens — detalhamento

| Técnica | Economia | Onde |
|---|---|---|
| Prompt caching Anthropic (`ephemeral`) | 70% multi-turno | Bloco sistema + taxonomia |
| Cache de contexto por query-hash (5 min) | 40–60% queries similares | `orchestrator.py` |
| History compactation | 50% conversas longas | `orchestrator.compact_history` |
| Intent routing (pula retrieval) | 100% turnos skipáveis | `orchestrator.classify_intent` |
| Rerank com modelo barato | 80% no rerank | `retriever.rerank` |
| Chunk 600 tokens (vs 1k) | 20% contexto | `ingestion.py` |
| Metadata filtering pré-embedding | 30–50% menos chunks | `retriever.retrieve` |
| Truncamento inteligente (> 800t) | 25% long-form | `orchestrator.budget_enforce` |
| Streaming | Percepção | gateway |

**Budget-alvo**:
- Simples (saudação/definição): 400–900 tokens
- Médio (análise): 1800–2800 tokens
- Complexo (multi-aspect): 3500–5500 tokens (raro; warning)

## 7. Arquivos críticos

| Arquivo | Ação |
|---|---|
| `src/rag/{config,ingestion,retriever,orchestrator,prompts,telemetry,safety}.py` | **novo** |
| `src/common/llm_gateway.py` | **novo** — multiprovider |
| `scripts/{build_rag_corpus,rag_eval}.py` | **novo** |
| `apps/streamlit/layers/chat.py` | **novo** — aba chat |
| `apps/streamlit/components/chat_widget.py` | **novo** — drawer |
| `tests/unit/rag/test_{ingestion,retriever,orchestrator,safety}.py` | **novo** |
| `tests/integration/test_rag_pipeline.py` | **novo** — e2e mock LLM |
| `tests/fixtures/rag_eval.yaml` | **novo** — 20 perguntas |
| `docs/rag/{README,prompt-design}.md` | **novo** |
| `.env.example` | editar — seção RAG |
| `pyproject.toml` | editar — extras `rag` |

## 8. Reuso (não recriar)

- **`TextEmbeddingBuilder`** em `src/ml/features/text_embeddings.py` — gera embeddings MiniLM PT-BR.
- **Máscara PII** de `src/ml/models/erro_leitura_topic_model.py::mask_sensitive_text`.
- **Paleta ENEL + componentes** da Sprint 14 (`apps/streamlit/theme.py`, `components/narrative.py`).
- **Cache** de `src/viz/cache.py` (Sprint 14) aplicado em embedding de query (5 min TTL).
- **Logger** em `src/common/logging.py` — telemetria estende.

## 9. Verificação

```bash
# 1. Construir corpus
.venv/bin/python scripts/build_rag_corpus.py --rebuild
# Esperado: ~250 chunks, ~50k tokens, ~30s CPU

# 2. Unit
.venv/bin/python -m pytest tests/unit/rag/ -q --cov=src/rag

# 3. Integração (mock LLM)
.venv/bin/python -m pytest tests/integration/test_rag_pipeline.py -v

# 4. Eval gabarito
.venv/bin/python scripts/rag_eval.py
# Esperado: accuracy ≥ 80%, citation_rate ≥ 95%

# 5. Manual
export RAG_PROVIDER=anthropic RAG_API_KEY=sk-ant-...
.venv/bin/streamlit run apps/streamlit/erro_leitura_dashboard.py
# Checklist:
#  - saudação contextualizada
#  - 8 perguntas pré-existentes rodam
#  - streaming OK
#  - citações clicáveis abrem trecho
#  - trocar provider (OpenAI) via .env + reload → funciona
#  - feedback 👍/👎 persiste em data/rag/feedback.csv
#  - badge de tokens < 3k em pergunta típica

# 6. Telemetria
cat data/rag/telemetry.jsonl | jq .cost_usd_estimated | awk '{s+=$1} END {print s}'
# 20 queries teste ≤ $0.05 USD em Haiku
```

## 10. Definition of Done

- [ ] Gateway multi-provider (Anthropic + OpenAI + Ollama, testado ≥ 2)
- [ ] Corpus ChromaDB ≥ 200 chunks, metadata rica
- [ ] Retriever híbrido (MiniLM + rerank LLM) com filtros
- [ ] Orquestrador com intent routing, compactation, budget enforcement
- [ ] Prompt caching Anthropic ativo; cache hit ≥ 60% em 6 turnos
- [ ] UI chat: streaming + 8 perguntas + saudação + citações clicáveis
- [ ] Drawer lateral funcional em qualquer aba
- [ ] Safety: guardrails I/O + fallback out-of-scope
- [ ] Telemetria JSONL sem vazar texto
- [ ] Eval ≥ 80% accuracy, ≥ 95% citation rate
- [ ] First-token < 1.5s cache hit, < 4s cold
- [ ] Custo médio ≤ $0.005/turno em Haiku/mini
- [ ] Docs completos: sprint + README + prompt-design
- [ ] Cobertura ≥ 80% em `src/rag/*`
- [ ] Zero PII em telemetria (auditoria manual sobre 20 turnos)

## 11. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Custo LLM escala com uso | Budget hard-cap + rerank com modelo barato + cache agressivo |
| Alucinação em queries fora do corpus | Threshold de similaridade + fallback "não tenho essa informação" |
| Prompt injection via pergunta | `safety.py` entrada; lista de padrões conhecidos |
| ChromaDB perde consistência em re-ingestão | `build_corpus` usa transação atômica + backup do diretório |
| Provider específico indisponível | Gateway permite fallback via `.env`; circuit-breaker simples |
| PII em feedback CSV | Hash do prompt + sanitização antes de gravar |

## 12. Orçamento

**~6 dias eng-equivalentes**: config + gateway (0.5d) + ingestão (1d) + retriever híbrido (1d) + orquestrador + caching (1.5d) + UI chat (1d) + safety + eval + docs (1d).

## 13. Ordem recomendada (inter-sprint)

1. **Sprint 14 primeiro** — arquitetura modular, tema e cache são pré-requisitos duros da aba chat.
2. **Sprint 15** herda tema, componentes `layer_intro`, cache utilities.

---

## 14. Entrega Abril/2026 — Dados reais + LLM local funcionando

### Estado realizado (2026-04-15)

**LLM local funcionando**: `llama-cpp-python 0.3.20` + **Qwen2.5-3B-Instruct Q4_K_M** (2GB GGUF) em `data/rag/models/`. First-token típico ~30s, resposta completa ~2min em i7 CPU-only (sem GPU).

**Corpus hibrido**: 42 arquivos escaneados → **663 chunks indexados** em ChromaDB, incluindo:
- Documentação: `docs/**/*.md` + `README.md` + `CLAUDE.md` (chunks por header + 480 tokens)
- **Data cards reais** gerados por `src/rag/data_ingestion.py` a partir do silver `data/silver/erro_leitura_normalizado.csv` (184.690 ordens)

### Data cards indexados

Em vez de indexar linhas individuais (PII + volume), agregamos 8 cards analíticos:

1. **visao-geral** — total CE (172.568) + SP (12.122), refaturamento (11.0%), causa-raiz rotulada (31.7%)
2. **regiao-ce** — top 5 assuntos + top 5 causas-raiz do Ceará
3. **regiao-sp** — top 5 assuntos + top 5 causas-raiz de São Paulo
4. **top-assuntos** — top 12 assuntos da base (refaturamento domina)
5. **top-causas-raiz** — top 12 causas rotuladas (multa autoreligação, erro digitação, GD, média)
6. **refaturamento** — ordens resolvidas via refaturamento por região
7. **evolucao-mensal** — série 2025-01 a 2026-03 com barras ASCII
8. **grupo-tarifario** — GB domina, seguido de GA e GD

### Chat UI premium

`apps/streamlit/layers/chat.py` reescrito com:
- Hero gradiente ENEL (vermelho → magenta) como greeting cold
- Status panel lateral: modelo, provider (local 🔒), índice (✅/⚠️)
- Chips categorizados por expanders: 📘 Regras, 🧠 Modelos, 📊 Dashboard, 🏗 Arquitetura, 🚀 Sprints, **📈 Dados** (expandido por default)
- **Streaming token-a-token via `st.write_stream`** — placeholder com cursor "▌" durante geração
- Typing indicator "Assistente ENEL está pensando…" antes do 1º token
- Pills de metadata: intent, tokens (cores semafóricas), latência total, 1º token, nº de fontes
- Citações como bloco Markdown ao final; history corta citações antigas ao enviar p/ LLM
- Feedback 👍/👎 por turno com log CSV

### Roteamento ajustado

`route_doc_types` agora reconhece termos analíticos ("quantos", "volume", "CE", "SP", "causa-raiz"…) e direciona retrieval para `["data", "business", "viz"]`, priorizando os cards.

### Ajuste de threshold

`RAG_SIMILARITY_THRESHOLD` default baixado de 0.25 → 0.05 porque o embedder default é **hashing local determinístico** (não MiniLM), cujos scores cosine ficam entre 0.1-0.25. Pode ser sobreposto via env.

### Validação

Pergunta: *"Quantas reclamações temos no total entre CE e SP?"*
- Retrieval trouxe `data/silver/...#visao-geral` e `#regiao-sp`
- Qwen respondeu: **"184.690 reclamações reais"** — número exato dos data cards
- Tempo total: ~2min primeiro turno (KV cache frio), ~40s subsequentes
