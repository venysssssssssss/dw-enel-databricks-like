{{ config(materialized='table', unique_key='sk_uc') }}

select
    {{ generate_surrogate_key('cast(cod_uc as varchar)') }} as sk_uc,
    cod_uc,
    cod_base,
    classe_consumo,
    tipo_ligacao,
    status_uc,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('stg_cadastro_ucs') }}
