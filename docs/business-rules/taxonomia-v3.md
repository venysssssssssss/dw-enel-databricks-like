# Taxonomia v3 — Classificador `erro_leitura`

## Objetivo

A taxonomia v3 reduz o bucket `indefinido` sem trocar o motor determinístico do classificador. O contrato permanece CPU-only, baseado em keywords ponderadas, regex e mapeamento complementar de topic para causa canônica.

## Diferença vs v2

| Classe nova | Categoria | Severidade | Uso esperado |
|---|---|---|---|
| `procedimento_administrativo` | `resolucao_administrativa` | `low` | Resolução administrativa sem causa técnica explícita. |
| `ajuste_numerico_sem_causa` | `resolucao_administrativa` | `low` | Correção numérica de consumo, referência ou kWh sem evidência de causa raiz. |
| `texto_incompleto` | `qualidade_texto` | `low` | Texto truncado ou abreviado demais para inferência operacional. |
| `solicitacao_canal_atendimento` | `canal_atendimento` | `low` | Canal ou contato sem causa técnica associada. |

Essas classes são `low` por desenho: elas explicam linguagem de processo, resolução ou qualidade textual, não falha técnica do medidor/leitura.

## Confiança

`causa_canonica_confidence` pode ser:

| Valor | Regra |
|---|---|
| `high` | Sinal forte ou pré-classificação conservadora. |
| `low` | Sinal fraco-mas-único ou mapping de topic para causa. |
| `indefinido` | Sem sinal mínimo ou empate ambíguo. |

As views de severidade SP usam `min_confidence="high"` por default para não inflar Alta/Crítica com classes de baixa confiança.

## Mapping de topics

`data/model_registry/erro_leitura/topic_to_canonical.csv` só atua quando o keyword classifier devolve `indefinido`. Um label forte nunca é sobrescrito por topic.

## Contrato de dados

Colunas paralelas aceitas no silver:

| Coluna | Descrição |
|---|---|
| `causa_canonica_v3` | Label v3 materializado por backfill. |
| `causa_canonica_confidence` | Bucket de confiança do label v3. |

Quando `causa_canonica_v3` não existe, `prepare_dashboard_frame` calcula o label por `causa_raiz`, fallback keyword e mapping de topic.

## Regras de manutenção

- Não criar classe catch-all genérica.
- Não elevar severidade das quatro classes v3 sem evidência de risco operacional.
- Toda nova classe deve entrar em `TAXONOMY` e aparecer em `taxonomy_metadata()`.
- Toda mudança de topic mapping deve manter `confidence=low` até validação humana.
