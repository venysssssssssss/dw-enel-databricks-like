{{ config(materialized='table', unique_key='sk_co') }}

select
    {{ generate_surrogate_key('cast(cod_co as varchar)') }} as sk_co,
    cod_co,
    cod_ut,
    nome_co,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('stg_cadastro_cos') }}
