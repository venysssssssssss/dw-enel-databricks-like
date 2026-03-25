SELECT
    dt.ano_mes,
    dd.nome_distribuidora,
    db.nome_base,
    m.valor_meta,
    m.valor_realizado,
    m.pct_atingimento,
    m.status_meta
FROM gold.fato_metas m
JOIN gold.dim_tempo dt ON m.sk_tempo = dt.sk_tempo
JOIN gold.dim_distribuidora dd ON m.sk_distribuidora = dd.sk_distribuidora
JOIN gold.dim_base db ON m.sk_base = db.sk_base
