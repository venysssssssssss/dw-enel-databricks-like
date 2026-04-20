{{ config(
    materialized='table',
    tags=['mis', 'executivo']
) }}

WITH silver_reclamacoes AS (
    -- Para o MVP, estamos lendo direto da Silver (Parquet/Iceberg).
    -- Em prod, seria {{ ref('stg_reclamacoes_ce') }}
    SELECT *
    FROM {{ source('silver', 'reclamacoes_ce_tratadas') }}
)

SELECT
    ordem AS ordem_id,
    instalacao AS instalacao_id,
    dt_ingresso AS data_ingresso,
    assunto,
    observacao_ordem_clean AS observacao_limpa,
    devolutiva_clean AS devolutiva_limpa,
    macrotema,
    causa_raiz_inferida,
    is_root_cause,
    ind_refaturamento,
    'CE' AS regiao,
    -- Regras adicionais de negócios para Criticidade (Mock)
    CASE 
        WHEN is_root_cause = true AND ind_refaturamento = 1.0 THEN 'high'
        WHEN is_root_cause = true THEN 'medium'
        ELSE 'low'
    END AS criticidade_operacional
FROM silver_reclamacoes
