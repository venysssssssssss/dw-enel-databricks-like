{{
    config(
        materialized='incremental',
        unique_key='cod_nota',
        incremental_strategy='merge'
    )
}}

with notas as (
    select *
    from {{ ref('stg_notas_operacionais') }}
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
    dl.sk_lote,
    di.sk_instalacao,
    duc.sk_uc,
    dcol.sk_colaborador,
    dr.sk_risco,
    n.cod_nota,
    n.dias_atraso,
    case when n.status_atraso = 'NO_PRAZO' then true else false end as flag_no_prazo,
    case when n.status in ('EXECUTADA', 'FECHADA') then true else false end as flag_executada,
    case when n.status_atraso = 'ATRASADO' then true else false end as flag_atrasada,
    case when n.status = 'DEVOLVIDA' then true else false end as flag_devolvida,
    case when n.status = 'CANCELADA' then true else false end as flag_cancelada,
    n.tipo_servico,
    n.status as status_nota,
    n.status_atraso,
    n.classificacao_acf_asf,
    n._source_run_id,
    {{ safe_current_timestamp() }} as _loaded_at
from notas n
left join {{ ref('dim_tempo') }} dt on n.data_criacao = dt.data
left join {{ ref('dim_distribuidora') }} dd on n.cod_distribuidora = dd.cod_distribuidora
left join {{ ref('dim_ut') }} du on n.cod_ut = du.cod_ut
left join {{ ref('dim_co') }} dc on n.cod_co = dc.cod_co
left join {{ ref('dim_base') }} db on n.cod_base = db.cod_base
left join {{ ref('dim_lote') }} dl on n.cod_lote = dl.cod_lote
left join {{ ref('dim_instalacao') }} di on n.cod_instalacao = di.cod_instalacao
left join {{ ref('dim_uc') }} duc on n.cod_uc = duc.cod_uc
left join {{ ref('dim_colaborador') }} dcol on n.cod_colaborador = dcol.cod_colaborador
left join {{ ref('dim_risco') }} dr
  on n.classificacao_acf_asf = dr.classificacao_acf_asf
 and n.flag_risco = dr.flag_risco
