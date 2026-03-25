{{ config(materialized='table', unique_key='sk_instalacao') }}

select
    {{ generate_surrogate_key('cast(cod_instalacao as varchar)') }} as sk_instalacao,
    cod_instalacao,
    cod_uc,
    endereco,
    tipo_instalacao,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('stg_cadastro_instalacoes') }}
