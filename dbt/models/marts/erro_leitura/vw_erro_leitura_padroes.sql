{{
    config(materialized='view')
}}

with aggregated as (
    select
        cast(null as integer) as topic_id,
        coalesce(causa_raiz, 'NAO_CLASSIFICADA') as topic_name,
        data_ingresso as data,
        count(*) as quantidade
    from {{ ref('fato_erro_leitura') }}
    group by 1, 2, 3
),

totals as (
    select sum(quantidade) as total from aggregated
)

select
    a.topic_id,
    a.topic_name,
    a.data,
    a.quantidade,
    round(100.0 * a.quantidade / nullif(t.total, 0), 2) as percentual
from aggregated a
cross join totals t
