{{
    config(materialized='table', unique_key='sk_causa_raiz')
}}

with causas as (
    select distinct
        coalesce(nullif(causa_raiz, ''), 'NAO_CLASSIFICADA') as causa_raiz
    from {{ source('silver', 'erro_leitura_normalizado') }}
)

select
    {{ generate_surrogate_key('causa_raiz') }} as sk_causa_raiz,
    causa_raiz,
    case
        when causa_raiz = 'NAO_CLASSIFICADA' then false
        else true
    end as flag_label_humano,
    {{ safe_current_timestamp() }} as _loaded_at
from causas
