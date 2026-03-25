{{ config(materialized='table', unique_key='sk_colaborador') }}

select
    {{ generate_surrogate_key('cast(cod_colaborador as varchar)') }} as sk_colaborador,
    cod_colaborador,
    nome_colaborador,
    equipe,
    funcao,
    {{ safe_current_timestamp() }} as _loaded_at
from {{ ref('stg_cadastro_colaboradores') }}
