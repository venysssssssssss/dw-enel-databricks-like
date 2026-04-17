# Sprint 17 — Treinamento Focalizado do Agente RAG em CE e SP

**Responsável executor**: GPT 5.3 Codex
**Duração**: 5 dias úteis
**Precedência**: Sprint 15 (RAG baseline) + Sprint 16 (data plane unificado)
**Status alvo**: MVP + Eval Gate aprovado

---

## 1. Contexto e Problema

O agente RAG construído nas Sprints 13–15 indexa **todo o corpus** do projeto
(docs técnicos + 7 data cards agregados globais) e responde sobre qualquer tema.
Duas lacunas críticas bloqueiam uso em produção:

### 1.1 Escopo regional difuso
Os data cards consolidam CE + SP + outras regiões sem filtro explícito.
Perguntas como *"Quantas reclamações de refaturamento existem?"* misturam
regiões. O requisito de negócio validado é: **o agente deve operar exclusivamente
sobre as regionais Ceará (CE) e São Paulo (SP)**, espelhando o dataset Silver
`data/silver/erro_leitura_normalizado.csv`.

### 1.2 Qualidade de resposta insuficiente
- Embeddings `hashing` 256-dim são determinísticos mas **não semânticos** —
  dependem 100% do BM25 lexical para recall de sinônimos PT-BR.
- Threshold `0.05` é conservador; testes usam `0.25`; produção nunca foi tunada.
- Pesos híbridos `0.75 cosine + 0.25 lexical` nunca foram ablados.
- Golden dataset tem **10 casos hardcoded** em `scripts/rag_eval.py`; sem
  versionamento, sem regressão contínua, sem métricas clássicas (recall@k, MRR,
  faithfulness, refusal rate, regional compliance).
- Parity test `tests/integration/test_rag_bi_parity.py` valida **1 KPI**.
- Prompt system não instrui o modelo a responder *exatamente* o que foi
  perguntado — respostas tendem a expandir com dados não-solicitados.

### 1.3 Resultado esperado
Um agente RAG que:
1. Responde **apenas** sobre CE/SP, recusando explícita e educadamente outras
   regiões brasileiras.
2. Cita fontes verificáveis (`[fonte: caminho#anchor]`) em 100% das respostas
   analíticas.
3. Responde **exatamente** o que o usuário perguntou — sem extrapolações.
4. Tem grounding numérico consistente com o BI (`DataStore.aggregate`).
5. É validado por golden dataset de 60 casos + 7 métricas-gate em CI.

---

## 2. Objetivos Mensuráveis

| Métrica | Baseline | Alvo S17 | Gate |
|---|---|---|---|
| Recall@5 (golden CE+SP) | ~0.60 | ≥ 0.85 | bloqueia merge |
| MRR@10 | n/d | ≥ 0.70 | informativo |
| Citation accuracy | n/d | ≥ 0.80 | bloqueia merge |
| Regional compliance | n/d | 1.00 | bloqueia merge |
| Refusal rate (out-of-regional) | ~0 | ≥ 0.95 | bloqueia merge |
| Answer exactness (keyword overlap vs forbidden) | n/d | ≥ 0.75 | bloqueia merge |
| Parity RAG ↔ BI (8 KPIs CE+SP) | 1/1 | 8/8 | bloqueia merge |
| Latência p50 | n/d | ≤ 1.8s | informativo |
| Latência p95 | n/d | ≤ 4.5s | informativo |

---

## 3. Entendimento dos Dados (pré-requisito)

O agente é treinado **exclusivamente** sobre:

### 3.1 Fonte primária
`data/silver/erro_leitura_normalizado.csv` — 184.690 linhas, 24 colunas, UTF-8.

| Recorte | CE | SP |
|---|---|---|
| Registros | 172.568 (93,4%) | 12.122 (6,6%) |
| Período | 2025-01-02 → 2026-03-26 | 2025-07-01 → 2026-03-24 |
| Top assunto | REFATURAMENTO PRODUTOS (22%) | ERRO DE LEITURA (95,1%) |
| Taxa refaturamento resolvido | 11,8% | **0,0%** ← data quality flag |
| Cobertura temporal | 450 dias | 267 dias |

### 3.2 Viés conhecido em SP
SP está **fortemente enviesado para ERRO_LEITURA** (95% dos registros) e
apresenta **taxa de refaturamento zerada**. O agente deve **sempre** anotar
este caveat ao responder sobre SP, citando o card `data-quality-notes`.

### 3.3 Glossário e regras (region-agnostic, mantidos no corpus)
- `docs/business-rules/01-business-glossary.md` — ACF/ASF, UT, CO, UC, Lote.
- `docs/business-rules/02-acf-asf-rules.md` — árvore de decisão.
- `docs/business-rules/03-operational-metrics.md` — refaturamento, efetividade.

### 3.4 Hierarquia operacional (relevante para cards)
```
Distribuidora (ENEL CE=3, ENEL SP=1)
  └─ UT → CO → Base/Polo → Lote → UC → Instalação
```

---

## 4. Arquitetura da Solução

### 4.1 Visão alto nível

```
┌──────────────────────────────────────────────────────────────────┐
│  Pergunta do usuário                                             │
└──────────────────────────────────────────────────────────────────┘
         │
         ▼
┌───────────────────────┐  safety.py: check_input, mask_pii
│ Input Validation      │  + is_out_of_regional_scope ← NOVO
└───────────────────────┘
         │ (se região ≠ CE/SP → early refusal)
         ▼
┌───────────────────────┐  orchestrator.py:
│ Intent + Region       │  - classify_intent (existe)
│ Detection             │  - detect_regional_scope ← NOVO
└───────────────────────┘
         │
         ▼
┌───────────────────────┐  retriever.py:
│ Retrieval com filtros │  where = {doc_type, region ∈ {CE,SP},
│ regionais             │           dataset_version}
└───────────────────────┘
         │
         ▼
┌───────────────────────┐  prompts.py v2.0.0:
│ Prompt v2 + grounding │  REGIONAL_SCOPE, ANSWER_EXACTNESS,
│ + data quality notes  │  DATA_QUALITY_CAVEATS
└───────────────────────┘
         │
         ▼
┌───────────────────────┐  llm_gateway.py (inalterado)
│ LLM (Qwen 2.5 3B GGUF)│
└───────────────────────┘
         │
         ▼
┌───────────────────────┐  safety.sanitize_output + telemetria
│ Output sanitization   │  + region_of_passages[] ← NOVO
└───────────────────────┘
```

### 4.2 Matriz de arquivos a modificar/criar

| Arquivo | Ação | Propósito |
|---|---|---|
| `src/data_plane/cards.py` | MODIFY | parâmetro `regional_scope`, cards `regiao-ce`, `regiao-sp`, `ce-vs-sp-*`, `data-quality-notes` |
| `src/data_plane/store.py` | MODIFY | filtro default `regiao ∈ {CE,SP}` em `_apply_filters` |
| `src/rag/ingestion.py` | MODIFY | metadata `region`, `scope`, `data_source` no Chroma upsert |
| `src/rag/retriever.py` | MODIFY | param `region`, filtro `where.region`, pesos 0.6/0.4, heurísticas regionais em `route_doc_types` |
| `src/rag/orchestrator.py` | MODIFY | `detect_regional_scope`, `OUT_OF_REGIONAL_SCOPE` early return, propagação de `region` |
| `src/rag/prompts.py` | MODIFY | `PROMPT_VERSION="2.0.0"`, blocos `REGIONAL_SCOPE`, `ANSWER_EXACTNESS_RULES`, `DATA_QUALITY_CAVEATS`, 5 few-shots |
| `src/rag/safety.py` | MODIFY | `is_out_of_regional_scope(question)` |
| `src/rag/config.py` | MODIFY | env `RAG_REGIONAL_SCOPE`, default `RAG_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `src/rag/telemetry.py` | MODIFY | campos `region_detected`, `region_of_passages`, `out_of_regional_scope`, `golden_case_id` |
| `src/rag/eval/__init__.py` | CREATE | módulo eval |
| `src/rag/eval/metrics.py` | CREATE | recall@k, MRR, NDCG, citation_accuracy, refusal_rate, regional_compliance, answer_exactness |
| `src/rag/eval/runner.py` | CREATE | carrega golden JSONL, executa via `RagOrchestrator`, agrega métricas |
| `src/rag/eval/llm_judge.py` | CREATE (opcional) | faithfulness via Qwen, gated `RAG_LLM_JUDGE=1` |
| `scripts/rebuild_rag_corpus_regional.py` | CREATE | rebuild idempotente, publica manifest |
| `scripts/rag_eval_regional.py` | CREATE | substitui `scripts/rag_eval.py`, grava reports JSON versionados |
| `tests/evals/rag_sp_ce_golden.jsonl` | CREATE | 60 casos |
| `tests/unit/rag/test_regional_scope.py` | CREATE | detect/is_out_of_regional_scope + filtros retriever |
| `tests/unit/rag/test_cards_regional.py` | CREATE | `build_data_cards(regional_scope)` gera chunks com metadata correto |
| `tests/unit/rag/test_prompts_v2.py` | CREATE | versão bump + blocos presentes |
| `tests/integration/test_rag_bi_parity.py` | MODIFY | 1 → 8 casos (4 CE + 4 SP) |
| `tests/integration/test_rag_regional_compliance.py` | CREATE | 10 queries, 0 passages fora de CE/SP |
| `Makefile` | MODIFY | targets `rag-rebuild`, `test-rag-evals` |
| `docs/rag/01-regional-scope.md` | CREATE | política de escopo |
| `docs/rag/02-evaluation.md` | CREATE | golden set, métricas, como rodar |
| `docs/rag/03-prompt-playbook.md` | CREATE | prompt v2 decomposto |

---

## 5. Especificação Detalhada por Módulo

### 5.1 `src/data_plane/cards.py`

**Nova assinatura**:
```python
def build_data_cards(
    store: DataStore,
    regional_scope: Literal["CE", "SP", "CE+SP"] = "CE+SP",
) -> list[Chunk]:
    ...
```

**Cards novos a gerar**:

| ID | Anchor | Conteúdo | Trigger |
|---|---|---|---|
| `regiao-ce` | `regiao-ce` | qtd_ordens, distribuição causa, taxa refaturamento, cobertura temporal | regional_scope in {CE, CE+SP} |
| `regiao-sp` | `regiao-sp` | idem + **aviso de viés** (95% erro_leitura, 0% refaturamento) | regional_scope in {SP, CE+SP} |
| `ce-vs-sp-causas` | `ce-vs-sp-causas` | tabela comparativa top-5 causas CE x SP | CE+SP |
| `ce-vs-sp-refaturamento` | `ce-vs-sp-refaturamento` | taxa refaturamento lado-a-lado | CE+SP |
| `ce-vs-sp-mensal` | `ce-vs-sp-mensal` | série temporal sobreposta CE x SP | CE+SP |
| `data-quality-notes` | `data-quality-notes` | caveats explícitos (SP enviesado, CE cobertura 450d) | sempre |

**Metadata obrigatória por chunk**:
```python
metadata = {
    ...  # existente
    "region": "CE" | "SP" | "CE+SP",
    "scope": "regional",           # vs "global" para docs técnicos
    "data_source": "silver.erro_leitura_normalizado",
    "dataset_version": store.version().hash,
}
```

### 5.2 `src/rag/retriever.py`

**Assinatura `retrieve`** ganha `region`:
```python
def retrieve(
    self,
    query: str,
    k: int = 12,
    doc_types: list[str] | None = None,
    dataset_version: str | None = None,
    region: Literal["CE", "SP", "CE+SP"] | None = None,
) -> list[Passage]:
```

**Where clause Chroma**:
```python
where: dict = {}
if doc_types:
    where["doc_type"] = {"$in": doc_types}
if dataset_version:
    where["dataset_version"] = dataset_version
if region == "CE":
    where["region"] = {"$in": ["CE", "CE+SP"]}
elif region == "SP":
    where["region"] = {"$in": ["SP", "CE+SP"]}
elif region == "CE+SP":
    where["region"] = {"$in": ["CE", "SP", "CE+SP"]}
# None → sem filtro regional (queries glossário/arquitetura)
```

**Pesos híbridos**: `0.60 * cosine + 0.40 * lexical` (ajustado para valorizar
BM25 PT-BR com novo embedder semântico).

**Regional hints em `route_doc_types`** (regex adicionais):
```python
if re.search(r"\b(ceará|ce)\b", q_lower):
    return ["data", "business", "viz"]  # já existe; garantir `region` hint
if re.search(r"\b(são paulo|sp)\b", q_lower):
    return ["data", "business", "viz"]
```

### 5.3 `src/rag/orchestrator.py`

**Nova função**:
```python
def detect_regional_scope(question: str) -> Literal["CE", "SP", "CE+SP", None]:
    q = question.lower()
    ce = bool(re.search(r"\b(ceará|cearense|fortaleza|\bce\b)", q))
    sp = bool(re.search(r"\b(são paulo|paulista|\bsp\b)", q))
    if ce and sp: return "CE+SP"
    if ce: return "CE"
    if sp: return "SP"
    return None  # caller decide default
```

**Fluxo `answer()` atualizado**:
```python
# 1. safety (existe)
if out_of_regional := is_out_of_regional_scope(sanitized):
    return RagResponse(
        text=OUT_OF_REGIONAL_SCOPE_MESSAGE,
        passages=[], intent="out_of_regional_scope", ...
    )

# 2. intent + region
intent = classify_intent(sanitized)
region = detect_regional_scope(sanitized)
if region is None and intent in ANALYTICAL_INTENTS:
    region = "CE+SP"  # default para queries analíticas

# 3. retrieval com filtro regional
passages = retriever.top_passages(
    sanitized, top_n=5, doc_types=route_doc_types(sanitized),
    dataset_version=dataset_version, region=region,
)
# ... (resto inalterado)
```

**Mensagem padrão**:
```python
OUT_OF_REGIONAL_SCOPE_MESSAGE = (
    "Este assistente responde apenas sobre as regionais **Ceará (CE)** e "
    "**São Paulo (SP)**. Para outras regiões, consulte o dashboard regional "
    "ou a equipe de dados."
)
```

### 5.4 `src/rag/safety.py`

```python
_OTHER_REGIONS = re.compile(
    r"\b(rio de janeiro|minas gerais|bahia|pernambuco|paraná|paraíba|"
    r"rio grande|goiás|mato grosso|santa catarina|amazonas|pará|maranhão|"
    r"alagoas|sergipe|piauí|tocantins|rondônia|acre|amapá|roraima|"
    r"espírito santo|distrito federal|\brj\b|\bmg\b|\bba\b|\bpe\b|\bpr\b|"
    r"\bpb\b|\brs\b|\bgo\b|\bmt\b|\bms\b|\bsc\b|\bam\b|\bpa\b|\bma\b|"
    r"\bal\b|\bse\b|\bpi\b|\bto\b|\bro\b|\bac\b|\bap\b|\brr\b|\bes\b|\bdf\b)",
    re.IGNORECASE,
)

def is_out_of_regional_scope(question: str) -> bool:
    q = question.lower()
    has_other = bool(_OTHER_REGIONS.search(q))
    has_ce_sp = bool(re.search(r"\b(ceará|ce|são paulo|sp)\b", q))
    return has_other and not has_ce_sp
```

### 5.5 `src/rag/prompts.py` — v2.0.0

```python
PROMPT_VERSION = "2.0.0"

SYSTEM_STATIC = """
Você é o Assistente ENEL para as regionais Ceará (CE) e São Paulo (SP).

ESCOPO REGIONAL:
- Responda APENAS sobre CE e SP. Para outras regiões, informe que não há dados.
- Se a pergunta não menciona região, assuma CE+SP combinado.

REGRAS DE EXATIDÃO DE RESPOSTA:
- Responda EXATAMENTE o que foi perguntado. Não expanda com dados não solicitados.
- Se a pergunta pede um número, dê o número com citação da fonte.
- Se a pergunta pede uma definição, dê a definição sem estatísticas extras.
- Nunca invente métricas, datas, nomes, códigos.

GROUNDING E CITAÇÕES:
- SEMPRE cite fontes no formato [fonte: caminho#anchor].
- Use APENAS o CONTEXTO RECUPERADO abaixo. Se a resposta não está no contexto, diga:
  "Não encontrei essa informação nos dados indexados de CE/SP."

CAVEATS DE QUALIDADE DE DADOS:
- SP tem forte viés (95% ERRO_LEITURA, 0% refaturamento resolvido). SEMPRE mencione
  este caveat quando a resposta envolver métricas de SP, citando [fonte: data-quality-notes].
- CE tem cobertura 2025-01-02 → 2026-03-26 (450 dias); SP: 2025-07-01 → 2026-03-24 (267 dias).

FORMATO:
- Português do Brasil, tom profissional, 2-5 parágrafos curtos.
- Recuse PII (CPF, email, telefone).
- Glossário: ACF/ASF, UC, Bronze/Silver/Gold (citar fontes quando usar).
"""

# 5 few-shots (3 CE, 2 SP) no final do SYSTEM_STATIC
```

### 5.6 `src/rag/eval/metrics.py`

Implementar **7 métricas puras** (sem deps pesadas):
- `recall_at_k(retrieved_ids, expected_ids, k) -> float`
- `mrr(retrieved_ids, expected_ids) -> float`
- `ndcg_at_k(retrieved_ids, expected_ids, k) -> float`
- `citation_accuracy(answer_text, expected_sources) -> float`
- `refusal_rate(answers, expected_refusal_flags) -> float`
- `regional_compliance(passages_region, allowed={"CE","SP","CE+SP"}) -> float`
- `answer_exactness(answer, expected_keywords, forbidden_keywords) -> float`

### 5.7 Golden dataset — `tests/evals/rag_sp_ce_golden.jsonl`

**Estrutura de cada caso**:
```json
{
  "id": "ce-001",
  "question": "Quantas ordens de refaturamento existem em CE?",
  "expected_intent": "analise_dados",
  "expected_region": "CE",
  "expected_sources": ["data::regiao-ce", "data::refaturamento"],
  "expected_keywords": ["172", "11,8%", "refaturamento"],
  "forbidden_keywords": ["São Paulo", "RJ", "Minas"],
  "answer_must_cite_numbers": true,
  "answer_must_refuse": false
}
```

**Distribuição dos 60 casos**:
- 25 CE-específicos (top causas, refaturamento, mensal, grupo, ACF/ASF em CE)
- 15 SP-específicos (erro_leitura, viés, cobertura temporal)
- 10 comparativos (CE vs SP em causas, refaturamento, volume, grupo)
- 5 out-of-regional (RJ, MG, BA, PE, nacional) → `answer_must_refuse=true`
- 5 out-of-thematic (futebol, culinária, programação genérica) → `answer_must_refuse=true`

### 5.8 Makefile targets

```makefile
rag-rebuild:
	python scripts/rebuild_rag_corpus_regional.py \
		--regional-scope ${REGIONAL_SCOPE:-CE+SP}

test-rag-evals:
	python scripts/rag_eval_regional.py \
		--golden tests/evals/rag_sp_ce_golden.jsonl \
		--gate-recall5 0.85 \
		--gate-regional-compliance 1.0 \
		--gate-refusal 0.95 \
		--gate-citation 0.80 \
		--gate-exactness 0.75

test-rag: test-rag-evals
	pytest tests/unit/rag/ tests/integration/test_rag_*.py -v
```

---

## 6. Plano Diário (5 dias)

### Dia 1 — Data Layer & Cards Regionais
- Modificar `src/data_plane/cards.py` com `regional_scope` + 6 novos cards.
- Modificar `src/data_plane/store.py` com filtro default CE/SP.
- Criar `tests/unit/rag/test_cards_regional.py` (≥ 8 casos).
- Criar `docs/rag/01-regional-scope.md`.
- **DoD**: `pytest tests/unit/rag/test_cards_regional.py` passa.

### Dia 2 — Ingestão, Embeddings, Retriever
- Modificar `src/rag/ingestion.py` com metadata `region`/`scope`/`data_source`.
- Trocar default embedding para `paraphrase-multilingual-MiniLM-L12-v2`.
- Modificar `src/rag/retriever.py` (filtro regional, pesos 0.6/0.4, hints regex).
- Criar `scripts/rebuild_rag_corpus_regional.py` + `make rag-rebuild`.
- **DoD**: `make rag-rebuild` gera `data/rag/corpus_manifest.json` com ≥ 20 docs
  region-agnostic + ≥ 8 cards regionais; query smoke retorna passages com
  metadata `region` preenchido.

### Dia 3 — Orchestrator, Prompts v2, Safety
- Implementar `detect_regional_scope` + `OUT_OF_REGIONAL_SCOPE` em orchestrator.
- Bump `PROMPT_VERSION="2.0.0"` + novos blocos em `prompts.py`.
- Implementar `is_out_of_regional_scope` em `safety.py`.
- Criar `tests/unit/rag/test_regional_scope.py` + `test_prompts_v2.py`.
- **DoD**: unit tests passam; query "E no Rio?" retorna refusal sem invocar LLM.

### Dia 4 — Golden Dataset + Eval Suite
- Escrever 60 casos em `tests/evals/rag_sp_ce_golden.jsonl` (peer-review 2 pessoas).
- Criar `src/rag/eval/metrics.py` + `runner.py` + `llm_judge.py` (opcional).
- Criar `scripts/rag_eval_regional.py` com CLI + gates.
- Expandir `tests/integration/test_rag_bi_parity.py` para 8 casos.
- Criar `tests/integration/test_rag_regional_compliance.py`.
- **DoD**: `make test-rag-evals` executa e imprime tabela de métricas.

### Dia 5 — Tuning, Smoke E2E, Docs
- Rodar eval completa, ajustar threshold/pesos para bater gates.
- Validar parity RAG ↔ BI (8/8).
- Escrever `docs/rag/02-evaluation.md` + `03-prompt-playbook.md`.
- Smoke E2E via API + Streamlit chat (4 queries CE, 2 SP, 2 out-of-scope).
- Atualizar telemetria Streamlit se necessário.
- Atualizar `CLAUDE.md` com novos env vars.
- **DoD**: todos os gates aprovados; sprint doc finalizado; PR aberto.

---

## 7. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| SentenceTransformer lento no i7-1185G7 | Média | Médio | Batch de 64, cache disco em `data/rag/embed_cache/`, fallback `RAG_EMBEDDING_MODEL=hashing` |
| Rebuild ChromaDB corrompe corpus | Baixa | Alto | Escrever em `chromadb_v2/`, swap atômico via `RAG_CHROMADB_PATH` env |
| Golden dataset enviesado (autor único) | Alta | Alto | Peer review obrigatório por DS + analista de negócio |
| SP viés engana modelo mesmo com caveat | Média | Médio | Card `data-quality-notes` forçado em top-3 quando SP detectado |
| Prompt v2 quebra respostas existentes | Baixa | Alto | Feature flag `RAG_PROMPT_VERSION=1.0.0` permite rollback |
| Embedding semântico falha a carregar | Média | Baixo | Fallback automático para `hashing` com warning em telemetria |
| Latência p95 estoura 4.5s | Média | Médio | KV cache llama-cpp, reduzir `retrieval_k` para 8 |

---

## 8. Verificação End-to-End

```bash
# 1. Rebuild corpus regional
make rag-rebuild REGIONAL_SCOPE=CE+SP

# 2. Unit + integration
make test-unit
make test-integration

# 3. Gate de eval
make test-rag-evals
#   Deve imprimir:
#   recall@5=0.87 | MRR=0.72 | citation=0.82 | regional=1.00
#   refusal=0.96 | exactness=0.78 | parity=8/8 | p50=1.6s | p95=4.1s
#   ✓ ALL GATES PASS

# 4. Smoke manual
curl -X POST localhost:8000/rag/answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"Quantas reclamações de refaturamento em CE?"}'
# → cita [data::regiao-ce] + [data::refaturamento], número consistente com BI

curl -X POST localhost:8000/rag/answer \
  -d '{"question":"Taxa de erro de leitura em SP?"}'
# → cita [data::regiao-sp] + [data::data-quality-notes] com caveat de viés

curl -X POST localhost:8000/rag/answer \
  -d '{"question":"E no Rio de Janeiro?"}'
# → OUT_OF_REGIONAL_SCOPE_MESSAGE, sem LLM call (latency < 50ms)

# 5. Telemetria
tail -20 data/rag/telemetry.jsonl | \
  jq '{q:.question_hash, intent, region_detected, regions:.region_of_passages, oors:.out_of_regional_scope}'
```

---

## 9. Entregáveis

1. **Código**: 9 arquivos modificados, 11 arquivos criados (ver §4.2).
2. **Dataset**: `tests/evals/rag_sp_ce_golden.jsonl` com 60 casos peer-reviewed.
3. **Scripts**: `rebuild_rag_corpus_regional.py`, `rag_eval_regional.py`.
4. **Testes**: +4 arquivos de testes novos + 2 expandidos.
5. **Docs**: `sprint-17-rag-sp-ce-training.md` (este), `docs/rag/01-03-*.md`.
6. **Makefile**: targets `rag-rebuild`, `test-rag-evals`, `test-rag`.
7. **Report**: eval report JSON em `data/rag/eval_reports/{timestamp}.json`.
8. **PR**: com todos os gates de CI verdes.

---

## 10. Rollback Plan

Em caso de regressão em produção:

1. `git revert` do merge da Sprint 17.
2. Restaurar corpus anterior: `RAG_CHROMADB_PATH=data/rag/chromadb_v1`.
3. Rollback de prompt: `RAG_PROMPT_VERSION=1.0.0`.
4. Fallback de embedding: `RAG_EMBEDDING_MODEL=hashing`.
5. Reexecutar eval antiga: `python scripts/rag_eval.py` (preservado).

---

## 11. Referências Técnicas

- Sprint 15 (baseline RAG): `docs/sprints/sprint-15-chat-rag-enel.md`
- Sprint 16 (data plane): `docs/sprints/sprint-16-react-rust-unified-data.md`
- Arquitetura RAG atual: `src/rag/` + relatório arquitetural em conversa Claude 2026-04-16
- Dataset Silver: `data/silver/erro_leitura_normalizado.csv`
- Regras de negócio: `docs/business-rules/01-03-*.md`
- ChromaDB docs: https://docs.trychroma.com/
- SentenceTransformers PT-BR: `paraphrase-multilingual-MiniLM-L12-v2`
