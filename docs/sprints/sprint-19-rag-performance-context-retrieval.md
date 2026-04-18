# Sprint 19 — RAG Performance, Contexto e Busca Semântica (CE/SP)

**Responsável executor**: Engenharia de Dados + Engenharia de Aplicação (Codex handoff-ready)  
**Período**: 2026-04-27 → 2026-05-08 (2 semanas)  
**Precedência**: Sprint 18 (RAG Semantic Intelligence)  
**Status alvo**: `DONE` com gates de qualidade aprovados  
**Objetivo macro**: elevar confiabilidade do chat RAG em produção com foco em três eixos: performance, gerenciamento de contexto e recuperação semântica.

---

## 1) Contexto e evidências (baseline oficial)

O relatório de avaliação regional mais recente (`data/rag/eval_reports/20260418T071521Z.json`) mostra evolução funcional, porém ainda distante do padrão de produção esperado para recuperação/citação:

| Métrica | Baseline atual |
|---|---:|
| cases | 80 |
| recall@5 | 0.5854 |
| mrr@10 | 0.5023 |
| ndcg@10 | 0.4790 |
| citation_accuracy | 0.1375 |
| refusal_rate | 0.9250 |
| fallback_guardrail_success | 1.0000 |
| regional_compliance | 1.0000 |
| answer_exactness | 0.8208 |
| latency_p50_ms (eval) | 4.69 |
| latency_p95_ms (eval) | 11.13 |
| all_gates_pass | **false** |

Principais lacunas observadas:

1. **Recall insuficiente** para vários casos CE/SP com anchors esperados no golden dataset.
2. **Citação inconsistente** nas respostas (principal causa de falha de gate).
3. **Gestão de contexto desigual entre clientes**:
- Streamlit envia histórico recente.
- Web chat não envia histórico no payload SSE.
4. **Overhead evitável na API**:
- Recriação do orquestrador por requisição.
- Recalcular `dataset_version` a cada request.
5. **Prompt estático extenso** (alto consumo de janela de contexto).

---

## 2) Objetivos da Sprint 19 (mensuráveis)

### 2.1 Gates bloqueantes (merge/release)

| Métrica | Baseline | Alvo Sprint 19 | Gate |
|---|---:|---:|---|
| recall@5 | 0.5854 | **>= 0.85** | bloqueia |
| citation_accuracy | 0.1375 | **>= 0.80** | bloqueia |
| regional_compliance | 1.0000 | **= 1.00** | bloqueia |
| refusal_rate | 0.9250 | **>= 0.95** | bloqueia |
| answer_exactness | 0.8208 | **>= 0.88** | bloqueia |
| all_gates_pass | false | **true** | bloqueia |

### 2.2 Metas informativas de performance

| Cenário | Métrica | Alvo |
|---|---|---:|
| `stub` local | p95 end-to-end | <= 1.5s |
| `llama_cpp` local | p95 end-to-end | <= 35s |
| `llama_cpp` local | first-token p95 | <= 8s |
| API `/v1/rag/stream` | overhead fixo por request | queda >= 30% vs baseline |

---

## 3) Escopo técnico (o que entra e o que não entra)

### 3.1 Em escopo

1. Otimizações de performance no caminho API/SSE.
2. Correções de contexto conversacional (paridade Streamlit/Web).
3. Melhorias de retrieval/ranking para elevar recall real.
4. Mecanismo determinístico de citação para elevar `citation_accuracy`.
5. Recalibração de métricas/golden para refletir anchors canônicos atuais.

### 3.2 Fora de escopo (Sprint 19)

1. Troca de banco vetorial (manter ChromaDB).
2. Migração de provider principal para API externa paga.
3. Redesenho do data plane CE/SP (apenas ajustes necessários para retrieval).
4. Reescrita completa de prompt stack (foco em otimização incremental e segura).

---

## 4) Backlog detalhado por prioridade (decision-complete)

## P0 — Obrigatório para fechar a sprint

### P0.1 API warm singleton de orquestrador RAG
**Problema**: orquestrador e provider são criados por request de streaming.  
**Mudança**: inicializar e manter instância reutilizável no ciclo de vida da API (app state/lifespan) com fallback resiliente.  
**DoD**:
- `/v1/rag/stream` não instancia orquestrador em cada request.
- teste de integração cobrindo reuso em múltiplas requisições sequenciais.
- medição comparativa documentada (cold/warm).

### P0.2 Cache de `dataset_version` com invalidação determinística
**Problema**: hash completo dos arquivos é recalculado em cada request.  
**Mudança**: cache local do resultado com invalidação por `size + mtime_ns` (ou TTL curto + verificação rápida).  
**DoD**:
- sem regressão de consistência na checagem de versão no header `X-Dataset-Version`.
- benchmark mostrando redução do overhead fixo por request.
- estratégia de fallback segura em caso de erro no cache.

### P0.3 Citação determinística pós-geração
**Problema**: `citation_accuracy` atual é o principal gargalo de gate.  
**Mudança**: anexar bloco de fontes deduplicado e consistente com passagens usadas, independentemente da variabilidade do modelo.  
**DoD**:
- 100% das respostas analíticas com bloco de fontes formatado.
- `citation_accuracy` >= 0.80 no eval regional.
- validação de deduplicação e ordenação estável de fontes.

### P0.4 Paridade de contexto entre Web e Streamlit
**Problema**: web chat envia apenas `question`; histórico não trafega para API.  
**Mudança**: enviar histórico recente no payload web, no mesmo padrão já consolidado no Streamlit.  
**DoD**:
- contrato do endpoint documentado e aplicado em ambos clientes.
- caso de teste cobrindo pergunta de follow-up dependente de turno anterior.
- sem regressão de UX no stream de tokens.

### P0.5 Memória conversacional compacta (resumo)
**Problema**: há função de sumarização disponível, mas não integrada ao fluxo.  
**Mudança**: ativar resumo automático quando histórico ultrapassar limiar de turns/tokens para preservar contexto útil com baixo custo.  
**DoD**:
- política de gatilho explícita (turns/tokens) e configurável.
- testes unitários para histórico curto vs longo.
- redução de `prompt_tokens` em conversas extensas sem queda de exatidão.

## P1 — Alto impacto, risco controlado

### P1.1 Diversificação de contexto (MMR/per-source cap)
**Mudança**: evitar top-N dominado por uma única fonte/anchor; maximizar cobertura sem sacrificar relevância.  
**DoD**:
- regra de diversidade parametrizada.
- testes demonstrando aumento de variedade de fontes no contexto.
- sem queda de `answer_exactness`.

### P1.2 Rerank adaptativo por confiança
**Mudança**: habilitar reranker apenas quando confiança do ranking base estiver baixa/ambígua.  
**DoD**:
- política de ativação documentada.
- melhoria em recall/mrr nos casos difíceis do golden.
- impacto de latência dentro das metas informativas.

### P1.3 Recalibração de pesos híbridos e bonuses
**Mudança**: ajustar pesos `cosine + lexical + bonuses` com base em ablação do golden CE/SP.  
**DoD**:
- relatório curto de ablação com configuração vencedora.
- atualização de defaults e documentação dos parâmetros.
- ganho líquido em recall@5 sem piorar compliance.

## P2 — Otimização incremental

### P2.1 Prompt profile por intenção
**Mudança**: reduzir prompt estático em cenários que não exigem todo o bloco de instruções (ex.: glossário vs análise comparativa).  
**DoD**:
- perfis de prompt documentados.
- redução observável de tokens fixos.
- sem aumento de respostas fora de escopo.

### P2.2 Telemetria operacional ampliada
**Mudança**: registrar estágios separados (`retrieval_ms`, `budget_ms`, `llm_ms`, `first_token_ms`, `cache_path`).  
**DoD**:
- schema de telemetria atualizado e retrocompatível.
- dashboard/consulta de apoio para leitura de p50/p95 por estágio.

---

## 5) Mudanças de interface/contrato previstas

1. **API `/v1/rag/stream`**
- manter wire-format SSE atual;
- formalizar suporte a `history` no payload para todos os clientes;
- manter validação de `X-Dataset-Version` com política de cache documentada.

2. **Configuração de runtime (env)**
- adicionar flags/configs para:
`RAG_HISTORY_SUMMARY_ENABLED`,
`RAG_HISTORY_SUMMARY_MAX_TURNS`,
`RAG_CONTEXT_DIVERSITY_ENABLED`,
`RAG_CONTEXT_DIVERSITY_PER_SOURCE_CAP`,
`RAG_DATASET_VERSION_CACHE_TTL_SEC`.

3. **Telemetria**
- expandir campos sem quebrar leitores atuais (append-only no JSONL).

---

## 6) Plano de testes e validação

### 6.1 Unitários

1. Citação determinística: deduplicação, ordem, formatação e cobertura de anchors.
2. Cache de dataset version: hit, miss, invalidação por alteração de arquivo.
3. Summary de histórico: gatilho, limite e fallback.
4. Diversidade de contexto: cap por fonte e manutenção de relevância mínima.

### 6.2 Integração

1. API stream em sequência de múltiplas requisições (validar warm path).
2. Web chat com follow-up contextual usando histórico real.
3. Regressão CE/SP para bloqueios regionais e out-of-scope.

### 6.3 Avaliação RAG (gate)

Executar:

```bash
python scripts/rag_eval_regional.py \
  --golden tests/evals/rag_sp_ce_golden.jsonl \
  --gate-recall5 0.85 \
  --gate-regional-compliance 1.0 \
  --gate-refusal 0.95 \
  --gate-citation 0.80 \
  --gate-exactness 0.88
```

Condição de pronto: `all_gates_pass = true` no report gerado.

### 6.4 Performance

1. Medir cold vs warm para `/v1/rag/stream`.
2. Medir impacto do cache de versão no overhead fixo.
3. Medir p50/p95 por provider (`stub`, `llama_cpp`) com amostra representativa.

---

## 7) Plano de rollout (baixo risco)

1. Ativar P0 atrás de flags por padrão conservador.
2. Liberar em ambiente de dev + validação de golden.
3. Liberar em staging com coleta de telemetria comparativa por 48h.
4. Promover para produção quando gates + latência alvo forem atendidos.

---

## 8) Plano de rollback

1. Desativar flags novas e retornar para estratégia anterior de contexto/ranking.
2. Reverter para comportamento pré-S19 de retrieval/citation se houver regressão de exatidão.
3. Em caso de instabilidade de warm singleton, fallback imediato para inicialização por request (temporário) com alarme operacional.

---

## 9) Riscos e mitigação

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Recall cair por excesso de compressão de contexto | média | alto | limites conservadores + ablação antes do rollout |
| Latência aumentar com reranker | média | médio | rerank adaptativo por confiança + timeout de proteção |
| Drift entre anchors do golden e corpus real | alta | médio | normalização/aliases no runner + revisão dataset |
| Regressão em follow-ups no web chat | média | alto | testes de integração com histórico multi-turn |
| Cache de versão gerar falso positivo | baixa | alto | invalidação por mtime/size + fallback de hash completo |

---

## 10) Entregáveis obrigatórios da Sprint 19

1. Implementação P0 completa com testes.
2. Relatório de avaliação CE/SP com gates aprovados.
3. Comparativo de performance (antes/depois) documentado.
4. Atualização de documentação técnica (RAG + API + runbook).
5. Checklist final de DoD assinado.

---

## 11) Definition of Done (Sprint 19)

Para considerar a sprint concluída:

1. Todos os itens P0 concluídos e validados.
2. `all_gates_pass = true` no eval regional oficial.
3. Sem regressão de regional compliance (mantido em 1.00).
4. Evidência de ganho de performance no path quente da API.
5. Documentação alinhada com comportamento final do sistema.

---

## 12) Observações finais

A Sprint 19 é deliberadamente focada em **confiabilidade operacional** do chat RAG.  
A estratégia não é "trocar tudo", e sim corrigir os pontos de maior retorno já identificados por métrica: recuperação, citação e contexto conversacional.
