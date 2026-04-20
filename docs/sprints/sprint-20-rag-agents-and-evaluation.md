# Sprint 20 — RAG Evolution: LLM Judge, Adaptive Rerank & Agentic Tooling

**Responsável executor**: Engenharia de Dados + Engenharia de IA  
**Período**: 2026-05-11 → 2026-05-22 (2 semanas)  
**Precedência**: Sprint 19 (RAG Performance, Contexto e Busca Semântica)  
**Status alvo**: `TODO`  
**Objetivo macro**: Evoluir o ecossistema RAG de um modelo puramente generativo/semântico para um sistema auto-avaliativo e com capacidades agentísticas iniciais, ativando mecanismos avançados de ranqueamento de forma eficiente.

---

## 1) Contexto e oportunidades de melhoria

Com a consolidação da performance e gestão de contexto na Sprint 19, o RAG atual (baseado em `Qwen2.5-3B-Instruct-GGUF` e `ChromaDB`) apresenta uma fundação sólida. Contudo, há oportunidades claras de melhoria identificadas na arquitetura atual:

1. **Reranker Desativado por Padrão**: A flag `RAG_RERANK_ENABLED` segue `False` no `RagConfig`. O ranqueamento adaptativo (introduzido na S19) precisa ser calibrado para não impactar a latência, tornando-se o padrão.
2. **Avaliação Estática vs Dinâmica**: Atualmente a avaliação depende de `rag_eval_regional.py` (golden dataset estático). A flag `llm_judge_enabled` está desativada. Precisamos de avaliação contínua em shadow mode ou amostragem.
3. **Limitações de Dados Estruturados**: O modelo de RAG atual foca em leitura de documentos (Lakehouse docs, etc.). Responder perguntas analíticas exatas sobre os dados reais (ex: sumarizar tabelas ou consultar faturas via Datastore) exige "Function Calling" (Agentic RAG).
4. **Provider Llama.cpp e Limites**: Usar CPU-only `q4_k_m` é ótimo para o MVP, mas testar offload para GPU local (vLLM) ou uso de providers Cloud em ambiente de homologação aceleraria o tempo de first-token.

---

## 2) Objetivos da Sprint 20 (mensuráveis)

### 2.1 Gates bloqueantes (merge/release)

| Métrica | Baseline (S19) | Alvo Sprint 20 | Gate |
|---|---:|---:|---|
| mrr@10 | ~0.65 | **>= 0.85** (com reranker) | bloqueia |
| ndcg@10 | ~0.60 | **>= 0.82** (com reranker) | bloqueia |
| answer_exactness | >= 0.88 | **>= 0.92** | bloqueia |
| tool_call_accuracy | N/A | **>= 0.85** | bloqueia |

### 2.2 Metas informativas de performance

| Cenário | Métrica | Alvo |
|---|---|---:|
| `llama_cpp` local com Reranker | latência retrieval p95 | <= 1.5s (acréscimo de max 500ms) |
| Pipeline LLM Judge | overhead na geração | Assíncrono (0ms user impact)|

---

## 3) Escopo técnico (o que entra e o que não entra)

### 3.1 Em escopo

1. **Adaptive Reranker**: Otimizar a performance do cross-encoder local e ativá-lo por padrão para consultas ambíguas.
2. **LLM as a Judge Pipeline**: Implementar um fluxo background onde requisições com feedback (up/down) ou amostras aleatórias são reavaliadas por um LLM mais robusto (ex: Claude 3.5 Sonnet via API ou Qwen 14B local) para gerar score de exatidão e citação.
3. **Agentic Tooling (PoC)**: Adicionar suporte ao modelo (seja via `Qwen` ou provider `openai`) para realizar *tool calls* na camada `DataStore` (ler cards, métricas básicas) antes de gerar a resposta.

### 3.2 Fora de escopo (Sprint 20)

1. Agentes autônomos multi-step complexos (apenas single-step tool call).
2. Substituição do banco vetorial.
3. Geração de código Python/SQL on-the-fly pelo LLM (apenas ferramentas pré-definidas no código).

---

## 4) Backlog detalhado por prioridade (decision-complete)

## P0 — Obrigatório para fechar a sprint

### P0.1 Ativação e Otimização do Reranker (Cross-Encoder)
**Problema**: Recuperação híbrida pura pode trazer documentos pouco relevantes no topo em queries complexas.  
**Mudança**: Trocar o `RAG_RERANK_ENABLED` para `True`. Avaliar conversão do modelo `ms-marco-MiniLM` para formato ONNX ou usar um BGE-Reranker mais leve para reduzir a latência de reranking.  
**DoD**:
- `mrr@10` e `ndcg@10` aumentam.
- Testes de carga atestam aumento de latência < 500ms no step de retrieval.

### P0.2 Implementação do Pipeline LLM Judge
**Problema**: Avaliação manual demorada e feedback implícito pouco acionável.  
**Mudança**: Habilitar a flag `llm_judge_enabled`. Criar um worker assíncrono (ou consumer de fila/telemetria) que lê os logs (`data/rag/telemetry.jsonl`) e usa uma API externa/interna pesada para avaliar `Context Precision`, `Faithfulness` e `Answer Relevance` nas respostas em produção.  
**DoD**:
- Tabela/Dashboard de LLM Judge operacional.
- worker assíncrono que não bloqueia o event loop do FastAPI.

### P0.3 Integração de Function Calling (Tool Use) no Orchestrator
**Problema**: Perguntas sobre "quantas UCs temos?" dependem do que está no texto vetorizado, não dos dados estruturados reais.  
**Mudança**: Estender o `RagOrchestrator` e `LLMProvider` para suportar o formato de ferramentas da OpenAI/Anthropic (ou grammar do llama_cpp). Criar uma ferramenta `get_metrics_summary()` vinculada ao `DataStore`.  
**DoD**:
- O orquestrador detecta quando a pergunta exige dados vivos, chama a tool, e insere o retorno estruturado no contexto.
- `tool_call_accuracy` monitorada no eval.

## P1 — Alto impacto, risco controlado

### P1.1 Expansão de Query Avançada (HyDE)
**Mudança**: Evoluir a expansão de query atual para gerar uma resposta hipotética (HyDE - Hypothetical Document Embeddings) usando um modelo rápido antes de buscar no ChromaDB, melhorando recall de perguntas vagas.  
**DoD**:
- Avaliação A/B no golden dataset provando ganho de Recall sem ferir severamente a latência.

### P1.2 Roteamento Semântico no Orchestrator
**Mudança**: O atual roteamento (`detect_regional_scope` e intenções baseadas em Regex/In) deve ser complementado por um Semantic Router leve que define o *workflow* da requisição (ex: Chitchat vs RAG Documental vs Agentic Tooling).  
**DoD**:
- Classificação correta de intenção em >= 95% do dataset de teste de router.

---

## 5) Plano de testes e validação

### 5.1 Unitários
1. **Tool Use**: Testar se os prompts/schemas de ferramentas são gerados corretamente para as engines.
2. **LLM Judge**: Mock de respostas do juiz, garantindo que a pontuação é calculada e persistida adequadamente.

### 5.2 Integração
1. Verificar a orquestração multi-step: `Classificar -> Decidir Tool -> Executar Tool -> Gerar Resposta Final`.

### 5.3 Avaliação RAG (gate)
Executar script de avaliação (`rag_eval_regional.py` atualizado) incluindo assertivas para uso correto de tools quando induzido e melhoria na ordenação (NDCG).

---

## 6) Riscos e mitigação

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Função LLM Tool Call falhar em modelos menores | Alta | Alto | Garantir strict prompt engineering ou fallback para RAG padrão caso o JSON da tool seja inválido. |
| Reranker estourar latência de API | Média | Alto | Limitar o número de documentos enviados ao reranker (`RAG_RERANK_TOP_N` < 15). |
| LLM Judge gerar falsos positivos/negativos | Média | Médio | Usar modelo frontier (ex: GPT-4o ou Sonnet 3.5) apenas para o Judge, isolando-o dos custos de produção. |
