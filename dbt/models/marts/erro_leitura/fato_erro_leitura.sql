{{
    config(
        materialized='incremental',
        unique_key='ordem',
        incremental_strategy='merge'
    )
}}

with base as (
    select *
    from {{ source('silver', 'erro_leitura_normalizado') }}
    where _data_type in ('erro_leitura', 'base_n1_sp')
    {% if is_incremental() %}
    and _processed_at > (select coalesce(max(_loaded_at), timestamp '1900-01-01') from {{ this }})
    {% endif %}
),

joined as (
    select
        dt.sk_tempo,
        dr.sk_regiao,
        dcr.sk_causa_raiz,
        b.ordem,
        b.instalacao,
        b.assunto,
        cast(b.dt_ingresso as date) as data_ingresso,
        b.status,
        b.causa_raiz,
        b._source_region as regiao,
        b._sheet_name,
        b._source_file,
        b.has_causa_raiz_label,
        b.flag_resolvido_com_refaturamento,
        case when b.flag_resolvido_com_refaturamento then 1 else 0 end as qtd_refaturamento,
        1 as qtd_erros,
        {{ safe_current_timestamp() }} as _loaded_at
    from base b
    left join {{ ref('dim_tempo') }} dt
        on cast(b.dt_ingresso as date) = dt.data
    left join {{ ref('dim_regiao') }} dr
        on b._source_region = dr.regiao
    left join {{ ref('dim_causa_raiz') }} dcr
        on coalesce(nullif(b.causa_raiz, ''), 'NAO_CLASSIFICADA') = dcr.causa_raiz
)

select * from joined
