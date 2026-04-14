select
    f.data_ingresso,
    f.regiao,
    f.causa_raiz,
    f.status,
    f.instalacao,
    f.assunto,
    f.qtd_erros,
    f.qtd_refaturamento,
    h.anomaly_score,
    h.is_anomaly
from gold.fato_erro_leitura f
left join gold.hotspots_erro_leitura h
    on f.regiao = h.regiao
    and coalesce(f.causa_raiz, 'NAO_CLASSIFICADA') = h.classe_erro
    and f.data_ingresso = h.data
