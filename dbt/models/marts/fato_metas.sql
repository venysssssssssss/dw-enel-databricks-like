{{ config(materialized='incremental', unique_key='cod_base || mes_referencia || indicador', incremental_strategy='merge') }}

with metas as (
    select *
    from {{ ref('stg_metas_operacionais') }}
    {% if is_incremental() %}
    where _processed_at > (select max(_loaded_at) from {{ this }})
    {% endif %}
)
select
    dt.sk_tempo,
    dd.sk_distribuidora,
    du.sk_ut,
    dc.sk_co,
    db.sk_base,
    m.indicador,
    m.mes_referencia,
    m.valor_meta,
    m.valor_realizado,
    m.pct_atingimento,
    m.status_meta,
    (m.valor_meta - m.valor_realizado) as gap_absoluto,
    {{ safe_current_timestamp() }} as _loaded_at
from metas m
left join {{ ref('dim_tempo') }} dt on cast(concat(m.mes_referencia, '-01') as date) = dt.data
left join {{ ref('dim_distribuidora') }} dd on m.cod_distribuidora = dd.cod_distribuidora
left join {{ ref('dim_ut') }} du on m.cod_ut = du.cod_ut
left join {{ ref('dim_co') }} dc on m.cod_co = dc.cod_co
left join {{ ref('dim_base') }} db on m.cod_base = db.cod_base
