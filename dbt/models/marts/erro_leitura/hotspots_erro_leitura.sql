{{
    config(materialized='table')
}}

select
    regiao,
    coalesce(causa_raiz, 'NAO_CLASSIFICADA') as classe_erro,
    data_ingresso as data,
    count(*) as qtd_erros,
    cast(0.0 as double) as anomaly_score,
    false as is_anomaly,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('fato_erro_leitura') }}
group by 1, 2, 3
