# Glossário Operacional de Negócio — ENEL

## Entidades Organizacionais

| Termo | Sigla | Definição | Exemplo |
|---|---|---|---|
| Distribuidora | - | Empresa distribuidora de energia que opera em uma ou mais regiões | ENEL SP, ENEL RJ, ENEL CE, ENEL GO |
| Unidade Técnica | UT | Divisão regional dentro de uma distribuidora | UT Norte, UT Sul |
| Centro Operacional | CO | Subdivisão operacional dentro de uma UT | CO Campinas, CO Sorocaba |
| Base Operacional | Base | Unidade física onde equipes estão alocadas | Base Vila Mariana |
| Polo | Polo | Similar a base, mas com escopo menor ou temporário | Polo Itaquera |
| Lote | Lote | Agrupamento de ordens de serviço para execução em campo | Lote 001/2026-03 |

## Entidades de Serviço

| Termo | Sigla | Definição |
|---|---|---|
| Unidade Consumidora | UC | Ponto de consumo de energia com medidor. É o "cliente" do ponto de vista técnico |
| Instalação | - | Endereço físico onde a UC está instalada. Uma instalação pode ter múltiplas UCs |
| Nota Operacional | Nota / OS | Ordem de serviço que representa uma atividade a ser executada em campo |
| Fatura | - | Documento de cobrança emitido para uma UC em um ciclo de faturamento |
| Colaborador | - | Profissional de campo que executa notas operacionais |

## Classificações ACF/ASF

### ACF — Atividade Comercial com Faturamento

Notas que envolvem atividade comercial com impacto em faturamento.

| Classificação | Descrição | Critério |
|---|---|---|
| ACF Tipo A | Alta criticidade | Envolve corte, religação ou substituição de medidor com impacto direto no faturamento |
| ACF Tipo B | Média criticidade | Verificação ou inspeção com possível reflexo no faturamento |
| ACF Tipo C | Baixa criticidade | Atividade administrativa ou documental relacionada ao faturamento |

### ASF — Atividade de Serviço em Campo

Notas que envolvem serviço de campo sem vínculo direto com faturamento.

| Classificação | Descrição | Critério |
|---|---|---|
| ASF Risco | Serviço em área ou condição de risco | Classificada por geolocalização, tipo de instalação ou histórico de incidentes |
| ASF Fora Risco | Serviço em condição normal | Não atende critérios de risco |

### Regra de Classificação Risco

```
SE (area_classificada_risco = TRUE)
   OU (historico_incidentes_12m >= 2)
   OU (tipo_instalacao IN ('subestação', 'alta_tensão'))
ENTÃO flag_risco = TRUE
SENÃO flag_risco = FALSE
```

## Status Temporais

### Status de Atraso

| Status | Definição | Cálculo |
|---|---|---|
| No Prazo | Nota executada antes ou na data prevista | `data_execucao <= data_prevista` |
| Pendente No Prazo | Nota ainda não executada, mas dentro do prazo | `data_execucao IS NULL AND data_atual <= data_prevista` |
| Pendente Fora do Prazo | Nota não executada e prazo já venceu | `data_execucao IS NULL AND data_atual > data_prevista` |
| Atrasado | Nota executada após a data prevista | `data_execucao > data_prevista` |

### Cálculo de Dias de Atraso

```
dias_atraso = CASE
    WHEN data_execucao IS NOT NULL AND data_execucao > data_prevista
        THEN DATEDIFF(data_execucao, data_prevista)
    WHEN data_execucao IS NULL AND data_atual > data_prevista
        THEN DATEDIFF(data_atual, data_prevista)
    ELSE 0
END
```

> **Regra importante**: Dias de atraso só consideram **dias úteis** quando a distribuidora configura assim. Verificar configuração por distribuidora.

## Efetividade Operacional

### Definição

Efetividade mede a proporção de notas executadas com sucesso dentro do prazo sobre o total de notas atribuídas.

```
efetividade_pct = (notas_executadas_no_prazo / total_notas_atribuidas) * 100
```

### Variações

| Métrica | Fórmula | Uso |
|---|---|---|
| Efetividade Bruta | executadas / total | Visão geral de produtividade |
| Efetividade Líquida | executadas_no_prazo / total | Produtividade com qualidade |
| Efetividade por Colaborador | executadas_por_colab / atribuidas_por_colab | Performance individual |
| Efetividade por Lote | executadas_no_lote / total_no_lote | Performance de rota |

## Entrega de Fatura

### Regras de Entrega

| Conceito | Regra |
|---|---|
| Fatura entregue | Registro de entrega confirmado (físico ou digital) |
| Prazo de entrega | Até 5 dias úteis antes do vencimento (varia por distribuidora) |
| Entrega vs Coordenada | Comparação entre ponto GPS da entrega e coordenada cadastrada da UC |
| Tolerância geográfica | Raio de 50-100 metros (configurável por distribuidora) |

### Cálculo de Entrega dentro da Coordenada

```
distancia_metros = HAVERSINE(lat_entrega, lon_entrega, lat_uc, lon_uc)
flag_dentro_coordenada = (distancia_metros <= tolerancia_metros)
```

## Inadimplência / Não Pagamento

### Definições

| Conceito | Definição |
|---|---|
| Fatura em aberto | Fatura emitida sem registro de pagamento |
| Inadimplente | UC com fatura(s) vencida(s) há mais de X dias (configurável, padrão 30) |
| Janela de análise | Período considerado para classificar inadimplência (ex: últimos 90 dias) |

### Classificação de Risco de Não Pagamento

```
risco_inadimplencia = CASE
    WHEN qtd_faturas_vencidas_90d >= 3 THEN 'ALTO'
    WHEN qtd_faturas_vencidas_90d >= 1 THEN 'MEDIO'
    WHEN historico_atrasos_12m >= 3    THEN 'MEDIO'
    ELSE 'BAIXO'
END
```

## Metas Operacionais

### Estrutura de Metas

Metas são definidas por:
- **Período**: mês de referência
- **Granularidade**: distribuidora > UT > CO > base/polo
- **Indicador**: tipo de meta (entrega, efetividade, leitura, etc.)

### Cálculo de Atingimento

```
pct_atingimento = (valor_realizado / valor_meta) * 100

status_meta = CASE
    WHEN pct_atingimento >= 100 THEN 'ATINGIDA'
    WHEN pct_atingimento >= 90  THEN 'EM_RISCO'
    WHEN pct_atingimento >= 70  THEN 'CRITICA'
    ELSE 'NAO_ATINGIDA'
END
```

### Projeção de Fechamento

Para predizer se a meta será atingida no fim do mês:

```
dias_uteis_restantes = dias_uteis_total_mes - dias_uteis_decorridos
media_diaria = valor_realizado / dias_uteis_decorridos
projecao = valor_realizado + (media_diaria * dias_uteis_restantes)
pct_projecao = (projecao / valor_meta) * 100
```

## Não Lidos (Leitura de Medidores)

### Definições

| Conceito | Definição |
|---|---|
| Leitura realizada | Medidor lido com sucesso pelo leiturista |
| Não lido | Tentativa de leitura sem sucesso |
| Impedimento | Motivo de não leitura (cão bravo, portão trancado, UC inacessível) |
| Releitura | Nova tentativa de leitura após não-lido |

### Motivos Padronizados de Não Leitura

| Código | Descrição |
|---|---|
| NL01 | Portão trancado / sem acesso |
| NL02 | Cão bravo / animal impedindo |
| NL03 | Medidor danificado |
| NL04 | Medidor inacessível (altura, obstrução) |
| NL05 | UC não localizada |
| NL06 | Área de risco / segurança |
| NL99 | Outros |
