{{ config(materialized='table', unique_key='sk_tempo') }}

select
    {{ generate_surrogate_key('data_ref') }} as sk_tempo,
    cast(data_ref as date) as data,
    cast(dia_semana as integer) as dia_semana,
    cast(dia_mes as integer) as dia_mes,
    cast(mes as integer) as mes,
    cast(trimestre as integer) as trimestre,
    cast(ano as integer) as ano,
    uf,
    cast(flag_feriado_nacional as boolean) as flag_feriado_nacional,
    cast(flag_feriado_uf as boolean) as flag_feriado_uf,
    cast(flag_dia_util as boolean) as flag_dia_util,
    cast(substr(data_ref, 1, 7) as varchar) as ano_mes,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('seed_dim_tempo') }}
