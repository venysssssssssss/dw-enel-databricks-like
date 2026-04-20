{{ config(
    materialized='table',
    tags=['mis', 'executivo']
) }}

WITH fct AS (
    SELECT * FROM {{ ref('fct_reclamacoes_classificadas') }}
)

SELECT
    DATE_TRUNC('month', data_ingresso) AS mes,
    regiao,
    macrotema,
    COUNT(ordem_id) AS total_reclamacoes,
    SUM(ind_refaturamento) AS total_refaturamentos,
    SUM(ind_refaturamento) * 1.0 / NULLIF(COUNT(ordem_id), 0) AS pct_refaturamento
FROM fct
GROUP BY 1, 2, 3
