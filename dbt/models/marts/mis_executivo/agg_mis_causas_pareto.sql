{{ config(
    materialized='table',
    tags=['mis', 'executivo']
) }}

WITH fct AS (
    SELECT * FROM {{ ref('fct_reclamacoes_classificadas') }}
    WHERE is_root_cause = true
)

SELECT
    regiao,
    macrotema,
    causa_raiz_inferida,
    COUNT(ordem_id) AS qtd_ocorrencias,
    SUM(ind_refaturamento) AS qtd_refaturamento,
    SUM(ind_refaturamento) * 1.0 / NULLIF(COUNT(ordem_id), 0) AS pct_refaturamento
FROM fct
GROUP BY 1, 2, 3
ORDER BY 4 DESC
