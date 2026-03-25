{{ config(materialized='table', unique_key='sk_lote') }}

with lots as (
    select distinct
        cod_lote,
        cod_base,
        tipo_servico
    from {{ ref('stg_notas_operacionais') }}
    where cod_lote is not null
)
select
    {{ generate_surrogate_key('cast(cod_lote as varchar)') }} as sk_lote,
    cod_lote,
    cod_base,
    tipo_servico,
    {{ safe_current_timestamp() }} as _loaded_at
from lots
