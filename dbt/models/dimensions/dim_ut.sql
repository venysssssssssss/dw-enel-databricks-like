{{ config(materialized='table', unique_key='sk_ut') }}

select
    {{ generate_surrogate_key('cast(cod_ut as varchar)') }} as sk_ut,
    cod_ut,
    cod_distribuidora,
    nome_ut,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('stg_cadastro_uts') }}
