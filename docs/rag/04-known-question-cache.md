# Cache de perguntas conhecidas do RAG

O cache de perguntas conhecidas acelera perguntas recorrentes do chat RAG sem
descolar a resposta do dataset atual. As perguntas ficam versionadas em código,
mas a resposta é montada a partir dos data cards vigentes e do `dataset_hash`.

## Como funciona

- `src/rag/known_questions.py` mantém as 150 variações observadas/esperadas.
- `src/rag/answer_cache.py` normaliza texto, faz match exato/fuzzy conservador e
  renderiza resposta com citações.
- `RagOrchestrator` consulta o cache depois de safety/intent/region e antes do
  retrieval semântico/LLM.
- Cache hit registra `cache_hit=true` na telemetria e não chama o provider LLM.
- O stream SSE envia `question_hash`, `cache_hit`, `cache_seed_id` e `latency_ms`
  no evento `done`.

## Warmup

Para aquecer data plane e materializar um snapshot local das respostas conhecidas:

```bash
poetry run python scripts/cache_warmup.py --rag-known-answers
```

O arquivo gerado fica em `data/rag/known_answers.json`. Esse caminho é runtime
local e não deve ser commitado.

## Telemetria

Para resumir perguntas reais, latência e cobertura estimada dos seeds:

```bash
poetry run python scripts/analyze_rag_telemetry.py
```

Campos relevantes:

- `cache_hit_rate`: taxa real pós-implantação.
- `estimated_known_coverage`: quanto da telemetria atual casa com os seeds.
- `latency_total_ms`: p50, p95 e máximo.
- `top_question_previews`: previews mais frequentes sem expor texto completo.

## SLA

- Perguntas conhecidas: resposta via cache, meta operacional até 35s.
- Perguntas desconhecidas: retrieval + LLM, stream encerrado em até
  `RAG_STREAM_TOTAL_TIMEOUT_SEC` segundos, default `60`.

Se uma pergunta desconhecida estourar o limite, o SSE retorna uma mensagem de
timeout controlada para o usuário reformular.

## Manutenção

Ao adicionar nova pergunta:

1. Adicione a variação ao seed existente quando a resposta usar os mesmos anchors.
2. Crie novo seed só se a pergunta exigir outro conjunto de anchors ou outra regra.
3. Rode os testes de cache e orquestrador.
4. Rode a análise de telemetria para confirmar aumento de cobertura.
