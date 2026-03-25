select
    cod_distribuidora,
    nome_distribuidora,
    uf,
    case
        when uf in ('SP', 'RJ', 'ES', 'MG') then 'SUDESTE'
        when uf in ('CE', 'PE', 'BA') then 'NORDESTE'
        when uf in ('GO', 'DF', 'MT') then 'CENTRO-OESTE'
        else 'OUTRAS'
    end as regiao
from {{ source('silver', 'cadastro_distribuidoras') }}
