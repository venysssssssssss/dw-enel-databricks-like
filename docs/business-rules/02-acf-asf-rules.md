# Regras de Classificação ACF/ASF — Detalhamento Completo

## Visão Geral

A classificação ACF/ASF é o principal eixo de categorização de notas operacionais na ENEL. Toda nota deve ser classificada em um destes dois grupos, e dentro de cada grupo recebe uma subclassificação.

## Árvore de Decisão Completa

```
NOTA OPERACIONAL
│
├── Tem impacto no faturamento?
│   │
│   ├── SIM → ACF (Atividade Comercial com Faturamento)
│   │   │
│   │   ├── Envolve corte/religação/troca medidor?
│   │   │   └── SIM → ACF Tipo A (Alta Criticidade)
│   │   │
│   │   ├── Envolve inspeção/verificação com reflexo?
│   │   │   └── SIM → ACF Tipo B (Média Criticidade)
│   │   │
│   │   └── Atividade administrativa/documental?
│   │       └── SIM → ACF Tipo C (Baixa Criticidade)
│   │
│   └── NÃO → ASF (Atividade de Serviço em Campo)
│       │
│       ├── Atende critério de risco?
│       │   └── SIM → ASF Risco
│       │
│       └── Não atende critério de risco?
│           └── ASF Fora Risco
```

## Regras de Negócio ACF

### ACF Tipo A — Alta Criticidade

**Condições (qualquer uma)**:
```sql
tipo_servico IN (
    'CORTE',
    'RELIGACAO',
    'SUBSTITUICAO_MEDIDOR',
    'INSTALACAO_MEDIDOR',
    'REGULARIZACAO_FRAUDE'
)
OR (tipo_servico = 'INSPECAO' AND resultado_inspecao = 'IRREGULARIDADE_CONFIRMADA')
```

**Prioridade operacional**: Máxima
**SLA padrão**: 24-48h (varia por distribuidora)
**Impacto no faturamento**: Direto e imediato

### ACF Tipo B — Média Criticidade

**Condições**:
```sql
tipo_servico IN (
    'INSPECAO_PROGRAMADA',
    'VERIFICACAO_MEDIDOR',
    'ATUALIZACAO_CADASTRAL_COM_MEDICAO',
    'REVISAO_LEITURA'
)
AND NOT classificado_como_tipo_a  -- não se qualificou como Tipo A
```

**Prioridade operacional**: Alta
**SLA padrão**: 3-5 dias úteis
**Impacto no faturamento**: Possível, depende do resultado

### ACF Tipo C — Baixa Criticidade

**Condições**:
```sql
tipo_servico IN (
    'ATUALIZACAO_CADASTRAL',
    'EMISSAO_SEGUNDA_VIA',
    'ALTERACAO_TITULARIDADE',
    'SOLICITACAO_HISTORICO'
)
AND flag_impacto_faturamento = TRUE  -- tem vínculo com faturamento, mas indireto
```

**Prioridade operacional**: Normal
**SLA padrão**: 5-10 dias úteis
**Impacto no faturamento**: Indireto ou administrativo

## Regras de Negócio ASF

### Critérios de Risco

Uma nota ASF é classificada como **Risco** quando atende a **pelo menos um** dos seguintes critérios:

```sql
-- Critério 1: Área geográfica de risco
EXISTS (
    SELECT 1 FROM areas_risco ar
    WHERE ST_CONTAINS(ar.geometria, POINT(nota.longitude, nota.latitude))
    AND ar.ativa = TRUE
)

-- Critério 2: Histórico de incidentes
OR (
    SELECT COUNT(*) FROM incidentes i
    WHERE i.cod_instalacao = nota.cod_instalacao
    AND i.data_incidente >= DATEADD(MONTH, -12, CURRENT_DATE)
) >= 2

-- Critério 3: Tipo de instalação de risco
OR nota.tipo_instalacao IN (
    'SUBESTACAO',
    'ALTA_TENSAO',
    'AREA_INDUSTRIAL_RISCO',
    'ZONA_RURAL_ISOLADA'
)

-- Critério 4: Horário restrito
OR nota.horario_agendado NOT BETWEEN '06:00' AND '18:00'

-- Critério 5: Flag manual de risco
OR nota.flag_risco_manual = TRUE
```

### ASF Risco

**Requisitos operacionais adicionais**:
- Equipe mínima de 2 colaboradores
- Equipamento de proteção individual (EPI) obrigatório
- Comunicação prévia ao CO responsável
- Registro fotográfico obrigatório

**SLA**: Variável por tipo de risco

### ASF Fora Risco

**Requisitos operacionais**: Padrão
**SLA**: 5-15 dias úteis dependendo do tipo de serviço

## Regras de Transição de Status

Uma nota pode mudar de classificação ao longo do seu ciclo de vida:

```
CRIADA → ATRIBUIDA → EM_CAMPO → EXECUTADA → FECHADA
   │         │           │          │
   │         │           │          └── Pode reabrir → REABERTA
   │         │           │
   │         │           └── Pode retornar → DEVOLVIDA (motivo obrigatório)
   │         │
   │         └── Pode cancelar → CANCELADA (aprovação gerencial)
   │
   └── Pode cancelar → CANCELADA (antes da atribuição, sem aprovação)
```

### Regras de Transição

| De | Para | Condição |
|---|---|---|
| CRIADA | ATRIBUIDA | Colaborador e data atribuídos |
| ATRIBUIDA | EM_CAMPO | Check-in do colaborador (GPS) |
| EM_CAMPO | EXECUTADA | Registro de execução com evidência |
| EXECUTADA | FECHADA | Validação de qualidade aprovada |
| EXECUTADA | REABERTA | Falha de qualidade ou complemento necessário |
| EM_CAMPO | DEVOLVIDA | Impedimento registrado com motivo |
| * | CANCELADA | Cancelamento com justificativa |

## Impacto na Modelagem

### Na Silver Layer

```python
# Classificação ACF/ASF aplicada na Silver
def classificar_nota(row):
    if row['flag_impacto_faturamento']:
        if row['tipo_servico'] in TIPOS_ACF_A:
            return 'ACF_A'
        elif row['tipo_servico'] in TIPOS_ACF_B:
            return 'ACF_B'
        else:
            return 'ACF_C'
    else:
        if avaliar_risco(row):
            return 'ASF_RISCO'
        else:
            return 'ASF_FORA_RISCO'
```

### Na Gold Layer (Métricas por Classificação)

```sql
-- Exemplo de mart: efetividade por classificação
SELECT
    d.nome_distribuidora,
    dt.ano_mes,
    f.classificacao_acf_asf,
    COUNT(*) AS total_notas,
    SUM(CASE WHEN f.flag_executada THEN 1 ELSE 0 END) AS executadas,
    SUM(CASE WHEN f.flag_no_prazo THEN 1 ELSE 0 END) AS no_prazo,
    ROUND(100.0 * SUM(f.flag_no_prazo::INT) / COUNT(*), 2) AS efetividade_pct
FROM gold.fato_notas_operacionais f
JOIN gold.dim_distribuidora d ON f.sk_distribuidora = d.sk_distribuidora
JOIN gold.dim_tempo dt ON f.sk_tempo = dt.sk_tempo
GROUP BY 1, 2, 3
```

## Validações de Qualidade (Great Expectations)

```yaml
# Testes para classificação ACF/ASF
expectations:
  - expectation_type: expect_column_values_to_be_in_set
    kwargs:
      column: classificacao_acf_asf
      value_set: ['ACF_A', 'ACF_B', 'ACF_C', 'ASF_RISCO', 'ASF_FORA_RISCO']

  - expectation_type: expect_column_values_to_not_be_null
    kwargs:
      column: classificacao_acf_asf

  - expectation_type: expect_column_pair_values_A_to_be_greater_than_B
    kwargs:
      column_A: data_prevista
      column_B: data_criacao
      or_equal: true
      # Data prevista deve ser >= data de criação
```
