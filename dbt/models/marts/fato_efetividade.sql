{{ config(materialized='table') }}

select
    f.sk_tempo,
    f.sk_base,
    f.sk_distribuidora,
    count(*) as total_notas,
    sum(case when f.flag_executada then 1 else 0 end) as notas_executadas,
    sum(case when f.flag_no_prazo then 1 else 0 end) as notas_no_prazo,
    sum(case when f.flag_devolvida then 1 else 0 end) as notas_devolvidas,
    round(100.0 * sum(case when f.flag_executada then 1 else 0 end) / count(*), 2) as efetividade_bruta_pct,
    round(100.0 * sum(case when f.flag_no_prazo then 1 else 0 end) / count(*), 2) as efetividade_liquida_pct,
    round(100.0 * sum(case when f.flag_devolvida then 1 else 0 end) / count(*), 2) as taxa_devolucao_pct,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('fato_notas_operacionais') }} f
group by 1, 2, 3
