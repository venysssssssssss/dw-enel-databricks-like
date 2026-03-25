-- Notas atrasadas por base e período
SELECT *
FROM gold.fato_notas_operacionais
WHERE flag_atrasada = true;

-- Entregas fora da coordenada
SELECT *
FROM gold.fato_entrega_fatura
WHERE flag_dentro_coordenada = false;

-- UCs inadimplentes 90+ dias
SELECT *
FROM gold.fato_pagamento
WHERE flag_inadimplente = true
  AND dias_atraso_pagamento >= 90;

-- Efetividade por colaborador
SELECT sk_colaborador, count(*) AS total_notas, sum(CASE WHEN flag_no_prazo THEN 1 ELSE 0 END) AS no_prazo
FROM gold.fato_notas_operacionais
GROUP BY 1;
