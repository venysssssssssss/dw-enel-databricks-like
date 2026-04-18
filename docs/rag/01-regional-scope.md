# RAG Regional Scope (CE/SP)

## Política

O assistente RAG desta base está restrito às regionais:

- Ceará (`CE`)
- São Paulo (`SP`)

Perguntas sobre outras regiões devem retornar recusa educada e explícita.

## Regras de execução

1. `is_out_of_regional_scope(question)` roda antes de retrieval e LLM.
2. Se a pergunta mencionar estados fora de CE/SP (sem CE/SP no texto), ocorre early return com mensagem padrão.
3. `detect_regional_scope(question)` define `region` para o retriever:
   - `CE` -> `where.region in ["CE", "CE+SP"]`
   - `SP` -> `where.region in ["SP", "CE+SP"]`
   - `CE+SP` -> `where.region in ["CE", "SP", "CE+SP"]`
   - `None` -> sem filtro regional (docs/glossário)
4. Para intenção analítica sem região explícita, default é `CE+SP`.

## Metadados obrigatórios de chunks

- `region`: `CE` | `SP` | `CE+SP`
- `scope`: `regional` (cards) ou `global` (docs técnicos)
- `data_source`: origem lógica (`silver.erro_leitura_normalizado` para cards)
- `dataset_version`: hash da versão do DataStore

## Caveat obrigatório de SP

Respostas com métricas de SP devem mencionar viés de cobertura, citando:

- `[fonte: data/silver/erro_leitura_normalizado.csv#data-quality-notes]`

## Cards disponíveis no corpus (Sprint 17.1)

### CE — Erros de leitura
- `ce-overview` — totais, taxas, refaturamento
- `ce-top-causas` — Pareto de causas canônicas
- `ce-mensal-causas` — série mensal por causa
- `ce-topicos` — distribuição de tópicos BERTopic
- `ce-refaturamento` — análise ACF/ASF
- `ce-regiao-ce` — âncora regional CE

### CE — Reclamações totais (universo 167 k ordens)
- `ce-top-instalacoes` — top instalações por volume de reclamações
- `ce-reclamacoes-totais-mensal-assuntos` — série mensal por assunto
- `ce-reclamacoes-totais-mensal-causas` — série mensal por causa canônica

### SP — Base N1
- `sp-n1-overview` — totais SP, taxa refaturamento
- `sp-n1-assuntos` — Pareto assuntos SP
- `sp-n1-causas` — Pareto causas SP
- `sp-n1-mensal` — série mensal SP
- `sp-n1-grupo` — distribuição por grupo operacional SP
- `sp-top-instalacoes` — top instalações SP

## Boost routing (Sprint 17.1)

O retriever aplica boost semântico com as seguintes regras, em ordem de prioridade:

1. **Pergunta sobre instalação / cliente individual** → boost `ce-top-instalacoes` (CE) e `sp-top-instalacoes` (SP). O agente responde com agregações, não com dados individuais.
2. **Pergunta mensal / temporal** → boost `ce-reclamacoes-totais-mensal-*` ou `sp-n1-mensal` conforme região detectada.
3. **Pergunta CE total / universo** → boost `ce-reclamacoes-totais-*`.
4. **Pergunta SP** → `_SP_BOOSTS` tuple boost `sp-n1-*`.
5. **Pergunta CE erros de leitura** → `_CE_BOOSTS` tuple boost `ce-*` exceto total.

Implementação: `src/rag/retriever.py::HybridRetriever._apply_card_boosts`.

## Política de query individual (MVP Sprint 17.1)

Perguntas sobre instalações, clientes ou ordens específicas são respondidas via cards
de top-instalações agregados — sem exposição de dados individuais. A gate de bloqueio
(`_INDIVIDUAL_CLIENT_PATTERN`) foi removida para permitir o demo MVP.
