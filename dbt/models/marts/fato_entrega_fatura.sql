{{ config(materialized='incremental', unique_key='cod_entrega', incremental_strategy='merge') }}

with entregas as (
    select *
    from {{ ref('stg_entregas_fatura') }}
    {% if is_incremental() %}
    where _processed_at > (select max(_loaded_at) from {{ this }})
    {% endif %}
)
select
    dt.sk_tempo,
    dd.sk_distribuidora,
    duc.sk_uc,
    db.sk_base,
    e.cod_entrega,
    e.cod_fatura,
    e.flag_entregue,
    e.dias_para_entrega,
    e.flag_antes_vencimento,
    e.flag_dentro_coordenada,
    e.distancia_metros,
    e._source_run_id,
    {{ safe_current_timestamp() }} as _loaded_at
from entregas e
left join {{ ref('dim_tempo') }} dt on e.data_emissao = dt.data
left join {{ ref('dim_distribuidora') }} dd on e.cod_distribuidora = dd.cod_distribuidora
left join {{ ref('dim_uc') }} duc on e.cod_uc = duc.cod_uc
left join {{ ref('dim_base') }} db on duc.cod_base = db.cod_base
