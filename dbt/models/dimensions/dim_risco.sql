{{ config(materialized='table', unique_key='sk_risco') }}

with risk_classification as (
    select distinct
        classificacao_acf_asf,
        flag_risco
    from {{ ref('stg_notas_operacionais') }}
)
select
    {{ generate_surrogate_key("coalesce(classificacao_acf_asf, '') || '-' || cast(coalesce(flag_risco, false) as varchar)") }} as sk_risco,
    classificacao_acf_asf,
    flag_risco,
    case
        when flag_risco then 'RISCO'
        else 'PADRAO'
    end as descricao,
    {{ safe_current_timestamp() }} as _loaded_at
from risk_classification
