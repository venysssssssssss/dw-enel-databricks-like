# Avaliação RAG CE/SP

## Golden dataset

Arquivo: `tests/evals/rag_sp_ce_golden.jsonl`

Cada linha JSON define:

- `id`, `question`
- `expected_intent`, `expected_region`
- `expected_sources`
- `expected_keywords`, `forbidden_keywords`
- `answer_must_cite_numbers`, `answer_must_refuse`

## Métricas

Implementadas em `src/rag/eval/metrics.py`:

- `recall@5`
- `mrr@10`
- `ndcg@10`
- `citation_accuracy`
- `refusal_rate`
- `regional_compliance`
- `answer_exactness`

## Runner e CLI

Runner:

- `src/rag/eval/runner.py`

CLI:

```bash
python scripts/rag_eval_regional.py \
  --golden tests/evals/rag_sp_ce_golden.jsonl \
  --gate-recall5 0.85 \
  --gate-regional-compliance 1.0 \
  --gate-refusal 0.95 \
  --gate-citation 0.80 \
  --gate-exactness 0.75
```

Saída:

- resumo das métricas no stdout
- report JSON em `data/rag/eval_reports/{timestamp}.json`
- exit code não-zero quando gate falha

## Alvo Make

```bash
make test-rag-evals
```
