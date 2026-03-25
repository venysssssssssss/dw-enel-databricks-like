SELECT
    dt.ano_mes,
    dd.nome_distribuidora,
    du.nome_ut,
    dc.nome_co,
    db.nome_base,
    COUNT(*) AS total_notas,
    SUM(CASE WHEN f.flag_executada THEN 1 ELSE 0 END) AS executadas,
    SUM(CASE WHEN f.flag_no_prazo THEN 1 ELSE 0 END) AS no_prazo,
    SUM(CASE WHEN f.flag_atrasada THEN 1 ELSE 0 END) AS atrasadas,
    ROUND(100.0 * SUM(CASE WHEN f.flag_no_prazo THEN 1 ELSE 0 END) / COUNT(*), 2) AS efetividade_pct,
    ROUND(AVG(f.dias_atraso), 1) AS atraso_medio
FROM gold.fato_notas_operacionais f
JOIN gold.dim_tempo dt ON f.sk_tempo = dt.sk_tempo
JOIN gold.dim_distribuidora dd ON f.sk_distribuidora = dd.sk_distribuidora
JOIN gold.dim_ut du ON f.sk_ut = du.sk_ut
JOIN gold.dim_co dc ON f.sk_co = dc.sk_co
JOIN gold.dim_base db ON f.sk_base = db.sk_base
GROUP BY 1, 2, 3, 4, 5
