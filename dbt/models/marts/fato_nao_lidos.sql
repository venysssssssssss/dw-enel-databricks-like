{{ config(materialized='table') }}

select
    cast(null as varchar) as cod_tentativa,
    cast(null as varchar) as motivo_nao_leitura,
    cast(false as boolean) as flag_lido,
    cast(false as boolean) as flag_releitura,
    {{ safe_current_timestamp() }} as _loaded_at
where 1 = 0
