{{ config(materialized='table', unique_key='sk_distribuidora') }}

select
    {{ generate_surrogate_key('cast(cod_distribuidora as varchar)') }} as sk_distribuidora,
    cod_distribuidora,
    nome_distribuidora,
    uf,
    regiao,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('stg_cadastro_distribuidoras') }}
