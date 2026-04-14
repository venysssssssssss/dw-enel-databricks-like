{{
    config(materialized='table', unique_key='sk_regiao')
}}

with regioes as (
    select distinct
        _source_region as regiao
    from {{ source('silver', 'erro_leitura_normalizado') }}
)

select
    {{ generate_surrogate_key('regiao') }} as sk_regiao,
    regiao,
    case
        when regiao = 'CE' then 'Ceara'
        when regiao = 'SP' then 'Sao Paulo'
        else 'Nao informado'
    end as nome_regiao,
    {{ safe_current_timestamp() }} as _loaded_at
from regioes
