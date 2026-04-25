# Validação da Taxonomia v3

## Protocolo

A validação humana deve usar 200 linhas estratificadas:

| Estrato | Linhas |
|---|---:|
| v2 `indefinido` e v3 definido | 50 |
| v3 `indefinido` residual | 50 |
| v3 `confidence=high` | 50 |
| v3 `confidence=low` | 50 |

Campos mínimos da amostra:

- `ordem`
- `_source_region`
- `_data_type`
- `texto_completo`
- `causa_raiz`
- `causa_canonica_v3`
- `causa_canonica_confidence`
- `topic_id`
- `topic_name`

## Comando de apoio

```bash
poetry run python scripts/relabel_erro_leitura.py --report --benchmark
```

O relatório `reports/relabel_v3.json` deve registrar cobertura global, por região, por classe e por bucket de confiança.

## Critérios de aprovação

| Critério | Meta |
|---|---:|
| `indefinido` SP | ≤ 25% |
| `indefinido` CE | ≤ 35% |
| Macro-F1 holdout humano | ≥ 0,78 |
| `confidence=low` global | ≤ 35% |
| Regressão Alta+Crítica SP | ≤ 5% |

## Resultado desta implementação

Status: pendente de validação humana sobre o silver completo.

Validações automatizadas cobertas:

- `tests/unit/test_erro_leitura_classifier_v3.py`
- `tests/unit/test_erro_leitura_ml.py`
- `tests/unit/viz/test_erro_leitura_dashboard_data.py`
- `tests/unit/test_sp_severidade_views.py`
- `tests/unit/test_data_plane_store.py`
- `tests/unit/test_data_plane_views.py`

## Decisão de cutover

Até a validação humana fechar, `causa_canonica_v3` deve ser tratada como coluna paralela. O cutover para substituir `causa_canonica` só deve ocorrer após aprovação deste documento com data, amostra e responsável.
