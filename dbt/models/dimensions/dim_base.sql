{{ config(materialized='table', unique_key='sk_base') }}

select
    {{ generate_surrogate_key('cast(cod_base as varchar)') }} as sk_base,
    cod_base,
    cod_co,
    nome_base,
    tipo_base,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('stg_cadastro_bases') }}
