# Métricas Operacionais — Definição e Cálculo

## Hierarquia de Métricas

Todas as métricas devem ser calculáveis nas seguintes granularidades:

```
Distribuidora → UT → CO → Base/Polo → Lote → Colaborador
```

E nas seguintes dimensões temporais:

```
Dia → Semana → Mês → Trimestre → Ano
```

---

## 1. Métricas de Entrega de Fatura

### 1.1 Taxa de Entrega

```sql
taxa_entrega_pct = (faturas_entregues / faturas_emitidas) * 100
```

| Parâmetro | Definição |
|---|---|
| faturas_emitidas | Total de faturas emitidas no período para o recorte |
| faturas_entregues | Faturas com registro de entrega confirmado |
| Período | Ciclo de faturamento (mensal) |

### 1.2 Prazo Médio de Entrega

```sql
prazo_medio_dias = AVG(DATEDIFF(data_entrega, data_emissao))
WHERE data_entrega IS NOT NULL
```

### 1.3 Entrega Antes do Vencimento

```sql
taxa_antes_vencimento_pct = (
    COUNT(CASE WHEN data_entrega <= data_vencimento - intervalo_dias THEN 1 END)
    / COUNT(faturas_entregues)
) * 100
```

`intervalo_dias`: 5 dias úteis (configurável por distribuidora)

### 1.4 Entrega dentro da Coordenada

```sql
taxa_coordenada_pct = (
    COUNT(CASE WHEN flag_dentro_coordenada = TRUE THEN 1 END)
    / COUNT(tentativas_entrega)
) * 100
```

---

## 2. Métricas de Efetividade

### 2.1 Efetividade Bruta

```sql
efetividade_bruta_pct = (notas_executadas / notas_atribuidas) * 100
```

### 2.2 Efetividade Líquida (No Prazo)

```sql
efetividade_liquida_pct = (notas_executadas_no_prazo / notas_atribuidas) * 100
```

### 2.3 Taxa de Devolução

```sql
taxa_devolucao_pct = (notas_devolvidas / notas_atribuidas) * 100
```

### 2.4 Produtividade por Colaborador

```sql
produtividade_media = AVG(notas_executadas_por_dia) GROUP BY colaborador
```

### 2.5 Retrabalho

```sql
taxa_retrabalho_pct = (
    COUNT(CASE WHEN qtd_execucoes > 1 THEN 1 END)
    / COUNT(notas_executadas)
) * 100
```

---

## 3. Métricas de Atraso

### 3.1 Taxa de Atraso

```sql
taxa_atraso_pct = (
    COUNT(CASE WHEN status_atraso IN ('ATRASADO', 'PENDENTE_FORA_PRAZO') THEN 1 END)
    / COUNT(total_notas)
) * 100
```

### 3.2 Atraso Médio

```sql
atraso_medio_dias = AVG(dias_atraso) WHERE dias_atraso > 0
```

### 3.3 Distribuição de Atraso por Faixa

| Faixa | Definição |
|---|---|
| Sem atraso | dias_atraso = 0 |
| 1-3 dias | 1 <= dias_atraso <= 3 |
| 4-7 dias | 4 <= dias_atraso <= 7 |
| 8-15 dias | 8 <= dias_atraso <= 15 |
| 16-30 dias | 16 <= dias_atraso <= 30 |
| 30+ dias | dias_atraso > 30 |

### 3.4 Aging de Pendências

```sql
-- Distribuição de notas pendentes por tempo de espera
SELECT
    CASE
        WHEN DATEDIFF(CURRENT_DATE, data_prevista) <= 0 THEN 'No prazo'
        WHEN DATEDIFF(CURRENT_DATE, data_prevista) <= 7 THEN '1-7 dias vencida'
        WHEN DATEDIFF(CURRENT_DATE, data_prevista) <= 15 THEN '8-15 dias vencida'
        WHEN DATEDIFF(CURRENT_DATE, data_prevista) <= 30 THEN '16-30 dias vencida'
        ELSE '30+ dias vencida'
    END AS faixa_aging,
    COUNT(*) AS qtd_notas
FROM silver.notas_operacionais
WHERE status NOT IN ('EXECUTADA', 'FECHADA', 'CANCELADA')
GROUP BY 1
```

---

## 4. Métricas de Inadimplência

### 4.1 Taxa de Inadimplência

```sql
taxa_inadimplencia_pct = (
    COUNT(DISTINCT uc WHERE faturas_vencidas > 0)
    / COUNT(DISTINCT uc)
) * 100
```

### 4.2 Valor em Aberto

```sql
valor_inadimplente_total = SUM(valor_fatura)
WHERE data_vencimento < CURRENT_DATE AND data_pagamento IS NULL
```

### 4.3 Aging de Inadimplência

| Faixa | Definição |
|---|---|
| 1-30 dias | Recém vencida |
| 31-60 dias | Em acompanhamento |
| 61-90 dias | Candidata a ação |
| 90+ dias | Inadimplência consolidada |

### 4.4 Recorrência de Inadimplência

```sql
perfil_inadimplencia = CASE
    WHEN qtd_meses_inadimplente_12m >= 6 THEN 'CRONICO'
    WHEN qtd_meses_inadimplente_12m >= 3 THEN 'RECORRENTE'
    WHEN qtd_meses_inadimplente_12m >= 1 THEN 'EVENTUAL'
    ELSE 'ADIMPLENTE'
END
```

---

## 5. Métricas de Metas

### 5.1 Percentual de Atingimento

```sql
pct_atingimento = (valor_realizado / valor_meta) * 100
```

### 5.2 Gap para Meta

```sql
gap_absoluto = valor_meta - valor_realizado
gap_pct = ((valor_meta - valor_realizado) / valor_meta) * 100
```

### 5.3 Projeção de Fechamento

```sql
-- Projeção linear baseada em dias úteis
dias_uteis_decorridos = COUNT(dias_uteis WHERE data <= CURRENT_DATE AND mes = mes_referencia)
dias_uteis_restantes = COUNT(dias_uteis WHERE data > CURRENT_DATE AND mes = mes_referencia)
media_diaria = valor_realizado / NULLIF(dias_uteis_decorridos, 0)
valor_projetado = valor_realizado + (media_diaria * dias_uteis_restantes)
pct_projecao = (valor_projetado / valor_meta) * 100
```

### 5.4 Status de Risco da Meta

```sql
status_risco_meta = CASE
    WHEN pct_projecao >= 100 THEN 'NO_CAMINHO'
    WHEN pct_projecao >= 95  THEN 'ATENCAO'
    WHEN pct_projecao >= 85  THEN 'RISCO'
    ELSE 'CRITICO'
END
```

---

## 6. Métricas de Não Lidos

### 6.1 Taxa de Não Leitura

```sql
taxa_nao_lidos_pct = (tentativas_sem_leitura / total_tentativas) * 100
```

### 6.2 Top Motivos de Não Leitura

```sql
SELECT motivo_nao_leitura, COUNT(*) AS ocorrencias,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM silver.leituras
WHERE flag_lido = FALSE
GROUP BY motivo_nao_leitura
ORDER BY ocorrencias DESC
```

### 6.3 Reincidência de Não Leitura

```sql
-- UCs com não-leitura recorrente
SELECT cod_uc, COUNT(*) AS meses_nao_lido
FROM silver.leituras
WHERE flag_lido = FALSE
AND data_referencia >= DATEADD(MONTH, -6, CURRENT_DATE)
GROUP BY cod_uc
HAVING COUNT(*) >= 3
```

---

## Regras Transversais

### Dias Úteis

O cálculo de dias úteis exclui:
- Sábados e domingos
- Feriados nacionais
- Feriados estaduais (por UF da distribuidora)
- Feriados municipais (por município da base)

A tabela `dim_tempo` deve conter `flag_dia_util` pre-calculado por distribuidora.

### Período de Referência

- **Mês operacional**: Pode não coincidir com mês calendário. Algumas distribuidoras operam com ciclo de faturamento que cruza meses.
- **Fechamento**: O fechamento mensal ocorre em data definida pela distribuidora, não necessariamente dia 30/31.

### Arredondamento

- Percentuais: 2 casas decimais, arredondamento HALF_UP
- Valores monetários: 2 casas decimais
- Dias: inteiros (truncamento, não arredondamento)
