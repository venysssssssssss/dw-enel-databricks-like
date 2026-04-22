# Sprint 22 — ONNX RAG Runtime 100% Otimizado para Superar o Default

**Responsável executor**: Engenharia de Dados + Engenharia de Aplicação + Rust/Core Runtime  
**Período sugerido**: 2026-05-25 -> 2026-06-05 (2 semanas)  
**Precedência**: Sprint 18 (Continuous Training + Rust Inference), Sprint 19 (RAG Performance), Sprint 20 (RAG Evaluation)  
**Status alvo**: `DONE` somente se ONNX bater o embedding default nos gates oficiais  
**Objetivo macro**: transformar o ONNX de fallback funcional em runtime de embedding principal, mais rápido e operacionalmente mais previsível que o default `SentenceTransformer`/PyTorch, sem perda de qualidade nas respostas RAG.

---

## 1) Contexto e evidências atuais

O projeto já possui um caminho ONNX funcional:

- `scripts/train_embedding_cpu.py` exporta `data/rag/models/enel-minilm-onnx/model.onnx`.
- O grafo ONNX expõe:
  - `sentence_embedding`: vetor 384D mean-pooled e normalizado L2.
  - `last_hidden_state`: compatibilidade com runtimes antigos.
- `src/rag/ingestion.py` carrega ONNX por:
  - `enel_core.OnnxEmbedder`, quando o wheel Rust está instalado.
  - fallback Python com `onnxruntime`, quando `enel_core` não está disponível.
  - fallback final para SentenceTransformers/Hashing.
- `rust/enel_core/src/onnx_embed.rs` já foi adaptado para preferir `sentence_embedding`.

### 1.1 Baseline medido em 2026-04-22

#### Benchmark API sem LLM, cache desativado

Relatório: `data/rag/eval_reports/api_embedding_benchmark_no_cache.json`

| Métrica | Normal | ONNX Python fallback |
|---|---:|---:|
| Perguntas | 20 | 20 |
| Erros | 0 | 0 |
| Cache hits | 1 | 1 |
| Latência média com cold start | 3120.5 ms | 1158.8 ms |
| Primeira pergunta | 43622.3 ms | 3259.0 ms |
| Warm avg, sem 1ª pergunta | 988.9 ms | 1048.3 ms |
| Qualidade automática | 0.9833 | 0.9833 |

Leitura: ONNX reduziu cold start drasticamente, mas em warm path ficou ligeiramente pior pelo fallback Python.

#### Benchmark API com LLM local Qwen2.5 3B, 30 perguntas

Relatório: `data/rag/eval_reports/api_embedding_benchmark_llm_30_ctx4096.json`

Configuração:

```bash
RAG_STREAM_TOTAL_TIMEOUT_SEC=300
RAG_ONNX_BATCH_SIZE=8
RAG_ONNX_INTRA_OP_THREADS=2
RAG_ONNX_INTER_OP_THREADS=1
python -u scripts/benchmark_rag_api_embeddings.py \
  --provider llama_cpp \
  --model-path data/rag/models/qwen2.5-3b-instruct-q4_k_m.gguf \
  --n-ctx 4096 \
  --max-turn-tokens 512 \
  --no-rebuild-normal \
  --no-rebuild-onnx \
  --output data/rag/eval_reports/api_embedding_benchmark_llm_30_ctx4096.json
```

| Métrica | Normal | ONNX Python fallback |
|---|---:|---:|
| Perguntas | 30 | 30 |
| Erros | 0 | 0 |
| Cache hits | 0 | 0 |
| Latência média | 17.10s | 18.76s |
| P50 | 13.72s | 18.30s |
| P95 | 28.11s | 33.07s |
| Warm avg, sem 1ª pergunta | 14.12s | 15.84s |
| Qualidade automática | 0.8667 | 0.8667 |
| Tamanho médio resposta | 287.3 chars | 287.3 chars |
| Vencedor por latência | Normal em 19 casos | ONNX em 8 casos |

Leitura: com LLM real, o gargalo dominante é geração no `llama_cpp`; o ONNX Python fallback não bateu o default no end-to-end.

### 1.2 Problemas observados

1. **ONNX ainda não roda no caminho Rust validado**
   - `cargo`/`rustfmt` não estavam disponíveis no host de teste.
   - `enel_core` não estava instalado na `.venv`.
   - O benchmark mediu `onnxruntime` Python, não o runtime alvo Rust.

2. **Sem quantização**
   - `model.onnx` atual é FP32.
   - Para CPU, INT8 dinâmico costuma ser o caminho mais promissor para reduzir latência e memória.

3. **Tokenização ainda está em Python no fallback**
   - `AutoTokenizer` + NumPy + ONNX Runtime Python adicionam overhead.
   - Runtime alvo deve usar `tokenizers` Rust.

4. **Batching seguro, mas conservador**
   - ONNX batchado em `RAG_ONNX_BATCH_SIZE=8` para não travar o PC.
   - Falta matriz de tuning por batch/thread/modelo.

5. **Benchmark end-to-end mascara custo de embedding**
   - Com LLM CPU, a diferença de embedding vira parcela pequena.
   - Precisamos de benchmark em três camadas: embed-only, retrieval-only e API+LLM.

6. **Qualidade empatada, não melhor**
   - O formato ONNX não melhora qualidade por si.
   - Para superar o default com qualidade, precisa haver paridade numérica forte e/ou fine-tuning melhor avaliado.

---

## 2) Objetivos mensuráveis da Sprint 22

### 2.1 Gates bloqueantes para ONNX virar default

| Gate | Baseline atual | Alvo Sprint 22 | Bloqueia? |
|---|---:|---:|---|
| `embed_one_p50_ms` ONNX Rust vs normal | não medido | >= 30% mais rápido | sim |
| `embed_batch_32_throughput` ONNX Rust vs normal | não medido | >= 2.0x maior | sim |
| rebuild Chroma 946 chunks | ONNX Python 271s, normal 251s | ONNX Rust INT8 <= 150s | sim |
| API sem LLM warm p50 | normal 768.9ms, ONNX 873.2ms | ONNX <= normal * 0.75 | sim |
| API com LLM 30 perguntas p50 | normal 13.72s, ONNX 18.30s | ONNX <= normal * 0.95 | sim |
| `answer_exactness` | 0.8667 empatado | ONNX >= normal - 0.01 | sim |
| `citation_accuracy` | 0.0 no benchmark LLM | ONNX >= normal | sim |
| Erros API | 0 | 0 | sim |
| OOM/travamento durante indexação | ocorreu antes do batching | 0 ocorrências | sim |

### 2.2 Metas informativas

| Métrica | Alvo |
|---|---:|
| `model_load_ms` ONNX Rust | <= 1.5s |
| Memória adicional no rebuild | <= 1.5GB acima do baseline |
| `query_embedding_ms` p95 | <= 50ms |
| Diferença cosseno entre PyTorch e ONNX FP32 | >= 0.999 média |
| Diferença cosseno entre PyTorch e ONNX INT8 | >= 0.985 média |
| Tamanho `model.int8.onnx` | <= 50% do FP32 |

---

## 3) Escopo técnico

### 3.1 Em escopo

1. Instalar, compilar e validar `enel_core` com `ort` em release.
2. Tornar o runtime Rust o caminho ONNX principal.
3. Gerar ONNX FP32 e ONNX INT8.
4. Preferir `model.int8.onnx` quando disponível, com fallback para FP32.
5. Criar benchmarks formais:
   - embed-only.
   - retrieval-only.
   - API sem LLM.
   - API com LLM.
   - rebuild/indexação.
6. Tuning de threads, batch size e providers ONNX Runtime.
7. Garantir paridade de qualidade e estabilidade operacional.
8. Documentar operação, rollback e critérios de promoção para default.

### 3.2 Fora de escopo

1. Trocar ChromaDB por outro vector DB.
2. Trocar o LLM principal.
3. Treinar um modelo embedding totalmente novo fora do fluxo atual.
4. Otimizar prompt ou geração LLM além do necessário para benchmark justo.
5. Usar GPU/CUDA como requisito obrigatório.

---

## 4) Arquitetura alvo

### 4.1 Caminho atual

```text
RAG API
  -> HybridRetriever
    -> _load_embedder(model_path)
      -> enel_core.OnnxEmbedder se instalado
      -> Python onnxruntime fallback
      -> SentenceTransformer/Hashing fallback
```

### 4.2 Caminho alvo

```text
RAG API
  -> HybridRetriever
    -> EmbedderRegistry singleton
      -> RustOnnxEmbedder(enel_core, model.int8.onnx preferencial)
        -> tokenizers Rust
        -> ONNX Runtime ort CPUExecutionProvider
        -> sentence_embedding já normalizado
      -> PythonOnnxEmbedder fallback controlado
      -> SentenceTransformer fallback explícito
```

### 4.3 Artefatos alvo

```text
data/rag/models/enel-minilm-onnx/
  model.onnx
  model.int8.onnx
  tokenizer.json
  tokenizer_config.json
  vocab.txt
  config.json
  onnx_manifest.json
```

`onnx_manifest.json` deve registrar:

```json
{
  "format_version": 1,
  "base_model": "sentence-transformers/all-MiniLM-L6-v2",
  "embedding_dim": 384,
  "outputs": ["sentence_embedding", "last_hidden_state"],
  "preferred_model": "model.int8.onnx",
  "fallback_model": "model.onnx",
  "quantization": "dynamic-int8",
  "created_at": "ISO-8601",
  "validation": {
    "onnx_checker": true,
    "cosine_parity_fp32_mean": 0.999,
    "cosine_parity_int8_mean": 0.985
  }
}
```

---

## 5) Backlog detalhado

## P0 — Bloqueante

### P0.1 Toolchain Rust reprodutível

**Problema**: `cargo` e `rustfmt` não estavam disponíveis no host de teste; isso impede validar `enel_core`.

**Mudança**:
- Documentar instalação mínima local.
- Adicionar fallback Docker para build se host não tiver Rust.
- Garantir `cargo check`, `cargo test`, `cargo clippy` e `rustfmt`.

**Arquivos**:
- `docs/sprints/sprint-22-rag-onnx-runtime-default.md`
- `rust/enel_core/Cargo.toml`
- `infra/dockerfiles/rust-builder.Dockerfile` se necessário
- `Makefile`

**Comandos alvo**:

```bash
cargo fmt --manifest-path rust/enel_core/Cargo.toml --check
cargo check --manifest-path rust/enel_core/Cargo.toml
cargo test --manifest-path rust/enel_core/Cargo.toml
cargo clippy --manifest-path rust/enel_core/Cargo.toml -- -D warnings
poetry run maturin develop --release --manifest-path rust/enel_core/Cargo.toml
```

**DoD**:
- Todos os comandos passam localmente ou via Docker.
- `poetry run python -c "import enel_core"` passa.

### P0.2 Runtime Rust ONNX principal

**Problema**: benchmark atual mede fallback Python, não Rust.

**Mudança**:
- Finalizar `enel_core.OnnxEmbedder`.
- Preferir output `sentence_embedding`.
- Manter fallback para `last_hidden_state`.
- Expor metadados simples ao Python:
  - `model_path`
  - `embedding_dim`
  - `runtime`
  - `thread_count`

**Arquivos**:
- `rust/enel_core/src/onnx_embed.rs`
- `rust/enel_core/src/lib.rs`
- `tests/unit/rag/test_ingestion.py`
- novo `tests/integration/test_onnx_embedder_runtime.py`

**DoD**:
- `enel_core.OnnxEmbedder("data/rag/models/enel-minilm-onnx").embed(["teste"])` retorna `list[list[float]]`.
- dimensão = 384.
- norma L2 ~ 1.0.
- batch vazio retorna `[]`.
- batch com 1, 8, 32 textos funciona.
- erro acionável quando falta `model.onnx`/`tokenizer.json`.

### P0.3 Quantização INT8

**Problema**: ONNX atual é FP32; CPU pode ganhar muito com INT8.

**Mudança**:
- Criar script de quantização dinâmica.
- Validar modelo quantizado com `onnx.checker`.
- Comparar embeddings FP32/PyTorch/INT8.
- Atualizar loader para preferir `model.int8.onnx`.

**Novo script**:
- `scripts/quantize_embedding_onnx.py`

**Comando alvo**:

```bash
poetry run python scripts/quantize_embedding_onnx.py \
  --model-dir data/rag/models/enel-minilm-onnx \
  --input model.onnx \
  --output model.int8.onnx \
  --validate
```

**DoD**:
- `model.int8.onnx` gerado.
- `onnx.checker.check_model` passa.
- `onnxruntime.InferenceSession` carrega o INT8.
- média de similaridade cosseno vs FP32 >= 0.985 em 200 frases reais do corpus.

### P0.4 EmbedderRegistry e singleton de modelos

**Problema**: carregamento repetido de modelo distorce latência e custo operacional.

**Mudança**:
- Criar registry/cache de embedders por `model_name`.
- Reutilizar instância em indexação e query.
- Evitar recriar `InferenceSession`, tokenizer e SentenceTransformer por chamada.

**Arquivos**:
- `src/rag/ingestion.py`
- possível novo `src/rag/embeddings.py`
- `tests/unit/rag/test_embeddings.py`

**DoD**:
- Dois calls consecutivos para `_load_embedder(path)` retornam embedder reaproveitado ou wrapper sobre sessão compartilhada.
- Flag para limpar cache em testes.
- Thread-safe para API.

### P0.5 Benchmarks oficiais por camada

**Problema**: end-to-end com LLM mascara o efeito do embedding.

**Mudança**:
- Criar benchmark único com modos:
  - `embed-one`
  - `embed-batch`
  - `rebuild-index`
  - `api-no-llm`
  - `api-llm`
  - `retrieval-quality`

**Arquivos**:
- Evoluir `scripts/benchmark_rag_api_embeddings.py`
- novo `scripts/benchmark_embedding_runtime.py`

**Saídas**:

```text
data/rag/eval_reports/onnx_runtime_benchmark_{timestamp}.json
data/rag/eval_reports/onnx_runtime_benchmark_{timestamp}.md
```

**DoD**:
- Benchmark roda normal vs ONNX Rust FP32 vs ONNX Rust INT8.
- Se `enel_core` não estiver instalado, marca `rust_unavailable` e falha no gate de promoção.
- Relatório traz cold/warm separados.
- Relatório traz qualidade por caso e latência por estágio.

### P0.6 Rebuild seguro do índice ONNX

**Problema**: criação inicial travou PC antes do batching.

**Mudança**:
- Batching controlado por env/config.
- Progresso por lote.
- Medição de memória quando possível.
- Limite conservador padrão.
- Fail-fast se batch causar erro de memória.

**Configuração alvo**:

```bash
RAG_ONNX_BATCH_SIZE=16
RAG_ONNX_INTRA_OP_THREADS=4
RAG_ONNX_INTER_OP_THREADS=1
RAG_ONNX_PREFER_INT8=1
```

**DoD**:
- Rebuild completo do índice ONNX sem travar host.
- Logs mostram progresso por lote.
- `946` chunks atuais indexados com sucesso.
- Tempo alvo <= 150s no host de referência.

## P1 — Alto impacto

### P1.1 Tuning de threads e batch size

**Mudança**:
- Rodar matriz controlada:
  - batch: 1, 4, 8, 16, 32, 64
  - intra threads: 1, 2, 4, 6
  - inter threads: 1, 2
  - modelo: FP32, INT8

**DoD**:
- Relatório identifica configuração vencedora por:
  - menor p50 query.
  - maior throughput batch.
  - rebuild sem OOM.
  - menor p95 API.
- Defaults atualizados no `.env.example`/docs.

### P1.2 Paridade numérica PyTorch x ONNX

**Mudança**:
- Criar dataset de frases de validação do corpus:
  - perguntas golden.
  - chunks representativos.
  - textos curtos/longos.
  - acentos/PT-BR.
  - strings vazias e muito pequenas.

**DoD**:
- FP32 ONNX cosseno médio >= 0.999 vs PyTorch.
- INT8 ONNX cosseno médio >= 0.985 vs PyTorch.
- Casos abaixo de threshold são salvos no relatório.

### P1.3 Retrieval quality isolada

**Mudança**:
- Medir top-k de retrieval antes da geração LLM:
  - recall@5
  - MRR@10
  - NDCG@10
  - anchors esperados
  - overlap normal vs ONNX

**DoD**:
- ONNX Rust FP32 não pode piorar recall@5 vs normal.
- ONNX INT8 pode ter tolerância máxima de -0.01.
- Relatório aponta casos em que o ranking diverge.

### P1.4 Fallback explícito e observável

**Problema**: fallback silencioso pode mascarar que ONNX não está sendo usado.

**Mudança**:
- Telemetria deve registrar:
  - `embedding_backend`: `rust_onnx_int8`, `rust_onnx_fp32`, `python_onnx`, `sentence_transformer`, `hashing`.
  - `embedding_model_path`.
  - `embedding_ms`.
  - `embedding_dim`.

**DoD**:
- Logs/telemetria permitem provar qual backend respondeu cada request.
- `RAG_REQUIRE_ONNX_EMBEDDING=1` falha se cair para Python/ST/Hashing.

## P2 — Otimização e hardening

### P2.1 Pré-tokenização opcional no rebuild

**Mudança**:
- Avaliar cache de tokenização para chunks durante rebuild.
- Útil se tokenização dominar tempo.

**DoD**:
- Benchmark comprova ganho >= 10% ou tarefa é descartada com evidência.

### P2.2 ONNX Runtime profiling

**Mudança**:
- Habilitar profiling opcional em `onnxruntime`/`ort`.
- Salvar trace por benchmark.

**DoD**:
- Perfil permite separar tokenização, runtime, pooling e serialização.

### P2.3 Empacotamento CI/CD do wheel Rust

**Mudança**:
- Build wheel `enel_core` em pipeline.
- Publicar artefato local ou anexar em release.

**DoD**:
- Ambiente novo consegue instalar `core` sem compilar manualmente.

---

## 6) Mudanças de interface e configuração

### 6.1 Variáveis de ambiente novas/confirmadas

```bash
RAG_EMBEDDING_MODEL=data/rag/models/enel-minilm-onnx
RAG_REQUIRE_ONNX_EMBEDDING=1
RAG_ONNX_PREFER_INT8=1
RAG_ONNX_BATCH_SIZE=16
RAG_ONNX_INTRA_OP_THREADS=4
RAG_ONNX_INTER_OP_THREADS=1
RAG_ONNX_MODEL_FILE=model.int8.onnx
RAG_ONNX_FALLBACK_MODEL_FILE=model.onnx
RAG_EMBEDDING_BACKEND_CACHE=1
```

### 6.2 Contrato do diretório de modelo

Obrigatório:

```text
model.onnx
tokenizer.json
config.json
```

Opcional preferencial:

```text
model.int8.onnx
onnx_manifest.json
```

### 6.3 Comportamento de fallback

| Condição | Comportamento |
|---|---|
| `RAG_REQUIRE_ONNX_EMBEDDING=1` e Rust ONNX indisponível | falhar |
| INT8 ausente, FP32 presente | usar FP32 e registrar fallback |
| Rust indisponível e require off | usar Python ONNX e registrar fallback |
| ONNX inválido e require off | cair para SentenceTransformer/Hashing |

---

## 7) Plano de implementação por fases

### Fase 1 — Build Rust e runtime mínimo

1. Instalar toolchain Rust ou preparar Docker.
2. Rodar `cargo check`.
3. Corrigir erros de API `ort`, se houver.
4. Rodar `maturin develop --release`.
5. Smoke Python de `enel_core.OnnxEmbedder`.

**Saída esperada**: runtime Rust carregando `model.onnx`.

### Fase 2 — Quantização e manifesto

1. Criar `scripts/quantize_embedding_onnx.py`.
2. Gerar `model.int8.onnx`.
3. Validar `onnx.checker`.
4. Gerar `onnx_manifest.json`.
5. Medir paridade FP32/INT8/PyTorch.

**Saída esperada**: diretório ONNX completo e versionado.

### Fase 3 — Registry e loader

1. Criar ou refatorar embedder loader.
2. Preferir Rust INT8.
3. Adicionar cache/singleton.
4. Adicionar telemetria de backend.
5. Preservar compatibilidade com hashing e SentenceTransformer.

**Saída esperada**: `_load_embedder` usando o backend correto de forma observável.

### Fase 4 — Benchmark e tuning

1. Rodar embed-only.
2. Rodar rebuild-index.
3. Rodar API sem LLM.
4. Rodar API com LLM 30 perguntas.
5. Rodar retrieval quality no golden.
6. Rodar matriz batch/threads.

**Saída esperada**: relatório comparativo com vencedor claro.

### Fase 5 — Promoção para default ou rollback

Se todos os gates passarem:

```bash
RAG_EMBEDDING_MODEL=data/rag/models/enel-minilm-onnx
RAG_REQUIRE_ONNX_EMBEDDING=1
RAG_ONNX_PREFER_INT8=1
```

Se algum gate falhar:

```bash
RAG_EMBEDDING_MODEL=data/rag/models/temp_pytorch
RAG_REQUIRE_ONNX_EMBEDDING=0
```

---

## 8) Plano de testes

### 8.1 Unitários

1. `_env_positive_int` com valores válidos/inválidos.
2. Loader ONNX escolhe INT8 quando existe.
3. Loader ONNX cai para FP32 quando INT8 falta.
4. `RAG_REQUIRE_ONNX_EMBEDDING=1` falha em fallback indevido.
5. Embedder retorna dimensão 384.
6. Vetores têm norma L2 ~ 1.0.
7. Batch vazio retorna lista vazia.
8. Manifesto inválido gera erro acionável.

### 8.2 Integração

1. `enel_core.OnnxEmbedder` com `model.onnx`.
2. `enel_core.OnnxEmbedder` com `model.int8.onnx`.
3. `_load_embedder("data/rag/models/enel-minilm-onnx")` usa Rust quando instalado.
4. Rebuild Chroma ONNX completo.
5. API `/v1/rag/stream` com ONNX strict.

### 8.3 Benchmarks obrigatórios

```bash
poetry run python scripts/benchmark_embedding_runtime.py \
  --normal-model data/rag/models/temp_pytorch \
  --onnx-model data/rag/models/enel-minilm-onnx \
  --modes embed-one embed-batch rebuild-index retrieval-quality api-no-llm api-llm \
  --output data/rag/eval_reports/onnx_runtime_benchmark.json
```

### 8.4 Avaliação RAG

```bash
poetry run python scripts/rag_eval_regional.py \
  --golden tests/evals/rag_sp_ce_golden.jsonl
```

Condição:

- ONNX >= normal em recall/MRR/NDCG dentro da tolerância.
- ONNX não piora regional compliance.
- ONNX não piora refusal behavior.

---

## 9) Critérios de decisão

### 9.1 ONNX vira default se

Todos forem verdadeiros:

1. `enel_core` Rust instalado e usado em runtime.
2. INT8 disponível e validado.
3. `embed-one` p50 >= 30% melhor que normal.
4. `embed-batch-32` throughput >= 2x normal.
5. Rebuild índice <= 150s no corpus atual.
6. API sem LLM warm p50 <= 75% do normal.
7. API LLM p50 <= 95% do normal.
8. Qualidade automática não piora além de 0.01.
9. Zero erros em 30 perguntas LLM.
10. Zero OOM/travamentos em rebuild.

### 9.2 ONNX fica como experimental se

Qualquer uma ocorrer:

1. Rust indisponível no ambiente alvo.
2. INT8 perde qualidade acima da tolerância.
3. Rebuild ONNX fica mais lento que normal.
4. API LLM end-to-end piora mais de 5%.
5. Há fallback silencioso para Python ONNX.

### 9.3 Rollback imediato se

1. `RAG_REQUIRE_ONNX_EMBEDDING=1` impede boot em produção.
2. Chroma recebe vetores com dimensão inconsistente.
3. OOM ou travamento volta a ocorrer.
4. `answer_exactness` cai mais de 0.03.
5. `regional_compliance` cai abaixo de 1.0.

---

## 10) Riscos e mitigação

| Risco | Probabilidade | Impacto | Mitigação |
|---|---:|---:|---|
| `ort` crate muda API ou falha no build | Média | Alto | Fixar versão, validar Docker, smoke Python |
| INT8 perde recall | Média | Alto | Gate de paridade e fallback FP32 |
| Tokenização domina latência | Média | Médio | Usar `tokenizers` Rust e profiling |
| LLM mascara ganhos de embedding | Alta | Médio | Benchmarks por camada |
| Batch alto causa OOM | Média | Alto | Defaults conservadores e matriz controlada |
| Fallback silencioso mascara problema | Alta | Alto | Telemetria + `RAG_REQUIRE_ONNX_EMBEDDING=1` |
| Wheel Rust difícil de instalar | Média | Alto | CI build wheel + Docker builder |

---

## 11) Entregáveis finais

1. `enel_core` compilado e instalado via `maturin develop --release`.
2. `model.int8.onnx` gerado e validado.
3. `onnx_manifest.json` criado.
4. Loader ONNX preferindo Rust INT8.
5. Fallbacks explícitos e observáveis.
6. Benchmarks por camada.
7. Relatório comparativo final:
   - normal
   - ONNX Python fallback
   - ONNX Rust FP32
   - ONNX Rust INT8
8. Documentação operacional.
9. Make targets.
10. Decisão formal: promover ONNX para default ou manter experimental.

---

## 12) Make targets sugeridos

```makefile
onnx-train:
	poetry run python scripts/train_embedding_cpu.py

onnx-quantize:
	poetry run python scripts/quantize_embedding_onnx.py \
		--model-dir data/rag/models/enel-minilm-onnx \
		--validate

onnx-rust-install:
	poetry run maturin develop --release --manifest-path rust/enel_core/Cargo.toml

onnx-rust-check:
	cargo fmt --manifest-path rust/enel_core/Cargo.toml --check
	cargo check --manifest-path rust/enel_core/Cargo.toml
	cargo clippy --manifest-path rust/enel_core/Cargo.toml -- -D warnings
	cargo test --manifest-path rust/enel_core/Cargo.toml

onnx-bench:
	RAG_REQUIRE_ONNX_EMBEDDING=1 \
	RAG_ONNX_PREFER_INT8=1 \
	poetry run python scripts/benchmark_embedding_runtime.py \
		--output data/rag/eval_reports/onnx_runtime_benchmark.json

onnx-api-llm-bench:
	RAG_STREAM_TOTAL_TIMEOUT_SEC=300 \
	poetry run python scripts/benchmark_rag_api_embeddings.py \
		--provider llama_cpp \
		--model-path data/rag/models/qwen2.5-3b-instruct-q4_k_m.gguf \
		--n-ctx 4096 \
		--max-turn-tokens 512 \
		--no-rebuild-normal \
		--no-rebuild-onnx \
		--output data/rag/eval_reports/api_embedding_benchmark_llm_30_onnx_default_candidate.json
```

---

## 13) Definition of Done

Sprint 22 só fecha como `DONE` se:

1. `cargo check/test/clippy/fmt` passam.
2. `maturin develop --release` instala `enel_core`.
3. ONNX Rust FP32 e INT8 passam smoke.
4. INT8 passa paridade mínima.
5. Rebuild ONNX não trava e bate meta.
6. Benchmark por camada prova ganho do ONNX.
7. Benchmark LLM 30 perguntas roda com 0 erros e 0 cache hits.
8. Qualidade ONNX não piora.
9. Relatório final está em `data/rag/eval_reports/`.
10. Docs de operação e rollback estão atualizados.

Se os gates de performance não forem atingidos, a sprint ainda pode fechar como `DONE-EXPERIMENTAL`, mas ONNX não vira default.

