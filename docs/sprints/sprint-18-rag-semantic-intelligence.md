# Sprint 18 — RAG Semantic Intelligence (CE/SP)

**Responsável executor**: Codex GPT-5  
**Período**: 2026-04-18 → 2026-04-25  
**Precedência**: Sprint 17 (RAG SP/CE training)  
**Objetivo macro**: elevar precisão semântica + capacidade analítica do chat para perguntas compostas orientadas a negócio.

---

## 1) Problemas observados em produção

1. Perguntas compostas por **tipo de medidor + motivo** (ex.: medidor digital) caíam em “Não encontrei”.
2. O retriever acertava “tipos de medidor em SP”, mas não fechava o drill-down:
   - “Dentro desse tipo, quais top 5 motivos?”
3. Perguntas explicativas (“o que é X e por que é recorrente?”) ainda oscilam entre resposta superficial e resposta incompleta.
4. Latência continua alta em casos longos, com risco de prompt excessivo no `llama_cpp`.

---

## 2) Metas de qualidade da Sprint 18

| Métrica | Baseline pós-S17 | Alvo S18 |
|---|---:|---:|
| Query success em perguntas compostas (medidor + motivo) | < 60% | >= 95% |
| Taxa de “Não encontrei” em perguntas cobertas por cards | ~12% | <= 2% |
| Acurácia de citação para perguntas analíticas | >= 0.80 | >= 0.90 |
| p95 de latência (CPU local) | variável | <= 35s |

---

## 3) Escopo técnico

### 3.1 Retrieval/Index Intelligence
- [x] Novo card analítico SP: **top causas por tipo de medidor**  
  Anchor: `sp-causas-por-tipo-medidor`.
- [x] Novo boost semântico para intenções:
  - `motivo/causa/assunto` + `medidor/digital/analógico/ciclométrico`
- [ ] Query decomposition para perguntas em duas etapas:
  1) entidade principal (tipo de medidor)
  2) métrica solicitada (top motivos, % no tipo, volume)
- [ ] Re-ranking semântico com sinal estrutural de card (anchor priors + region priors).

### 3.2 Data Plane
- [x] Nova view: `sp_causas_por_tipo_medidor`
  - top N tipos de medidor em SP
  - top 5 causas por tipo
  - `% dentro do tipo` para leitura gerencial.
- [ ] Nova view CE-total por assunto→causa (explicabilidade para “por que recorrente?” em CE).
- [ ] Consolidar taxonomia “motivo” (assunto + causa) em formato único para o LLM.

### 3.3 Prompt/Orchestration
- [x] Prompt atualizado com novo universo de dados (`sp-causas-por-tipo-medidor`).
- [ ] Template de resposta causal:
  - “o que é” (definição)
  - “por que recorrente” (drivers observáveis no dataset)
  - “o que fazer” (ação recomendada quando houver card de playbook)
- [ ] Guardrail para evitar resposta genérica quando houver card de drill-down disponível.

### 3.4 Qualidade e Testes
- [x] Testes unitários de boosts e presença de anchors atualizados.
- [x] Teste unitário da nova view `sp_causas_por_tipo_medidor`.
- [ ] Golden cases novos (mín. +20) focados em perguntas compostas e follow-up contextual.
- [ ] Métrica de fallback indevido por intent (quando havia card canônico disponível).

---

## 4) Entregáveis esperados

1. Resposta correta para:
   - “Dessas reclamações, quais os top 5 motivos para o medidor digital?”
2. Resposta explicativa robusta para:
   - “O que é REFATURAMENTO PRODUTOS e por que é recorrente?”
3. Relatório de avaliação S18 com:
   - taxa de sucesso por tipo de pergunta,
   - taxa de fallback indevido,
   - latência p50/p95.

---

## 5) Critérios de aceite

- Perguntas com combinação `tipo de medidor + motivo` não podem retornar “Não encontrei” quando houver dados em SP.
- Toda resposta analítica deve citar ao menos uma fonte canônica com anchor.
- Pipeline de testes unitários + integrações RAG relevantes em verde.
- Sem regressão nas respostas já estabilizadas na Sprint 17.

---

## 6) Riscos e mitigação

1. **Ambiguidade de “motivo”** (assunto vs causa):
   - Mitigação: priorizar causa canônica no drill-down e expor assunto quando útil.
2. **Prompt inflation** em local `llama_cpp`:
   - Mitigação: cards mais objetivos + limite de contexto + retries defensivos.
3. **Desbalanceamento SP/CE**:
   - Mitigação: reforço de escopo por região e anchors específicos por universo.
