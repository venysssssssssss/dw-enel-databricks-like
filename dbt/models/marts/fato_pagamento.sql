{{ config(materialized='incremental', unique_key='cod_pagamento', incremental_strategy='merge') }}

with pagamentos as (
    select *
    from {{ ref('stg_pagamentos') }}
    {% if is_incremental() %}
    where _processed_at > (select max(_loaded_at) from {{ this }})
    {% endif %}
)
select
    dt.sk_tempo,
    duc.sk_uc,
    db.sk_base,
    p.cod_pagamento,
    p.cod_fatura,
    p.valor_fatura,
    p.valor_pago,
    p.flag_inadimplente,
    p.dias_atraso_pagamento,
    p._source_run_id,
    {{ safe_current_timestamp() }} as _loaded_at
from pagamentos p
left join {{ ref('dim_tempo') }} dt on p.data_vencimento = dt.data
left join {{ ref('dim_uc') }} duc on p.cod_uc = duc.cod_uc
left join {{ ref('dim_base') }} db on duc.cod_base = db.cod_base
