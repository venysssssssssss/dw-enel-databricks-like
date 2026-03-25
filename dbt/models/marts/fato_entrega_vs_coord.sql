{{ config(materialized='table') }}

select
    sk_tempo,
    sk_distribuidora,
    sk_base,
    count(*) as tentativas_entrega,
    sum(case when flag_dentro_coordenada then 1 else 0 end) as entregas_dentro_coordenada,
    round(100.0 * sum(case when flag_dentro_coordenada then 1 else 0 end) / count(*), 2) as taxa_coordenada_pct,
    avg(distancia_metros) as distancia_media,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('fato_entrega_fatura') }}
group by 1, 2, 3
