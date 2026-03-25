# Fontes de Dados — Mapeamento e Estratégia de Ingestão

## Inventário de Fontes

### Fontes Mestres / Cadastrais

| Fonte | Tipo | Formato Esperado | Frequência | Estratégia |
|---|---|---|---|---|
| Cadastro de Distribuidoras | Mestre | CSV/API | Sob demanda | Snapshot |
| Cadastro de UTs | Mestre | CSV/API | Sob demanda | Snapshot |
| Cadastro de COs | Mestre | CSV/API | Sob demanda | Snapshot |
| Cadastro de Bases/Polos | Mestre | CSV/API | Sob demanda | Snapshot |
| Cadastro de UCs | Mestre | CSV/DB | Diária | Snapshot (volume grande → incremental após validação) |
| Cadastro de Instalações | Mestre | CSV/DB | Diária | Snapshot |
| Cadastro de Colaboradores | Mestre | CSV/API | Semanal | Snapshot |
| Áreas de Risco | Referência | Shapefile/GeoJSON | Mensal | Snapshot |
| Calendário Operacional | Referência | CSV | Anual | Snapshot com atualizações |

### Fontes Operacionais (Transacionais)

| Fonte | Tipo | Formato Esperado | Frequência | Estratégia | Watermark |
|---|---|---|---|---|---|
| Notas Operacionais | Transacional | CSV/DB | Diária | Incremental | `data_alteracao` |
| Entregas de Fatura | Transacional | CSV/DB | Diária | Incremental | `data_registro` |
| Leituras de Medidor | Transacional | CSV/DB | Diária | Incremental | `data_leitura` |
| Pagamentos | Transacional | CSV/DB | Diária | Incremental | `data_processamento` |
| Execuções em Campo | Transacional | CSV/DB | Diária | Incremental | `data_execucao` |
| Devoluções de Nota | Transacional | CSV/DB | Diária | Incremental | `data_devolucao` |

### Fontes de Fechamento / Metas

| Fonte | Tipo | Formato Esperado | Frequência | Estratégia |
|---|---|---|---|---|
| Metas Operacionais | Planejamento | Excel/CSV | Mensal | Snapshot por mês de referência |
| Fechamento Mensal | Consolidação | Excel/CSV | Mensal | Snapshot imutável |
| Relatório de Efetividade | Consolidação | Excel/CSV | Mensal | Snapshot por mês |
| Comparativo Entrega vs Coordenada | Operacional | CSV | Mensal | Snapshot por mês |

---

## Contratos de Dados por Fonte

### Contrato: Notas Operacionais

```yaml
source:
  name: notas_operacionais
  owner_tecnico: "TBD - definir na Fase 0"
  owner_negocio: "TBD - definir na Fase 0"
  sistema_origem: "TBD"
  formato: CSV  # ou API/DB
  encoding: UTF-8
  delimiter: ";"
  quote_char: '"'

schema:
  - name: cod_nota
    type: BIGINT
    nullable: false
    description: "Identificador único da nota operacional"

  - name: cod_uc
    type: BIGINT
    nullable: false
    description: "Código da unidade consumidora"

  - name: cod_instalacao
    type: BIGINT
    nullable: false
    description: "Código da instalação"

  - name: cod_distribuidora
    type: INTEGER
    nullable: false
    description: "Código da distribuidora"

  - name: cod_ut
    type: INTEGER
    nullable: false
    description: "Código da unidade técnica"

  - name: cod_co
    type: INTEGER
    nullable: false
    description: "Código do centro operacional"

  - name: cod_base
    type: INTEGER
    nullable: false
    description: "Código da base/polo"

  - name: cod_lote
    type: INTEGER
    nullable: true
    description: "Código do lote (pode ser nulo em notas avulsas)"

  - name: tipo_servico
    type: STRING
    nullable: false
    description: "Tipo de serviço da nota"
    allowed_values: ["CORTE", "RELIGACAO", "SUBSTITUICAO_MEDIDOR", "INSPECAO", ...]

  - name: data_criacao
    type: DATE
    nullable: false
    format: "yyyy-MM-dd"

  - name: data_prevista
    type: DATE
    nullable: true
    format: "yyyy-MM-dd"
    description: "Data limite para execução"

  - name: data_execucao
    type: DATE
    nullable: true
    format: "yyyy-MM-dd"

  - name: data_alteracao
    type: TIMESTAMP
    nullable: false
    format: "yyyy-MM-dd HH:mm:ss"
    description: "Watermark para carga incremental"

  - name: status
    type: STRING
    nullable: false
    allowed_values: ["CRIADA", "ATRIBUIDA", "EM_CAMPO", "EXECUTADA", "FECHADA", "DEVOLVIDA", "CANCELADA", "REABERTA"]

  - name: cod_colaborador
    type: INTEGER
    nullable: true
    description: "Colaborador atribuído"

  - name: latitude
    type: DOUBLE
    nullable: true

  - name: longitude
    type: DOUBLE
    nullable: true

quality:
  - test: row_count_minimum
    value: 100
    description: "Carga diária deve ter no mínimo 100 registros"

  - test: unique
    columns: [cod_nota, data_alteracao]
    description: "Nota + timestamp deve ser única"

  - test: not_null
    columns: [cod_nota, cod_uc, cod_distribuidora, status, data_criacao, data_alteracao]

  - test: referential_integrity
    column: cod_distribuidora
    reference: cadastro_distribuidoras.cod_distribuidora

ingestion:
  strategy: incremental
  watermark_column: data_alteracao
  partition_by: data_criacao
  dedup_key: [cod_nota]
  dedup_order: data_alteracao DESC
```

### Contrato: Entregas de Fatura

```yaml
source:
  name: entregas_fatura
  owner_tecnico: "TBD"
  owner_negocio: "TBD"
  formato: CSV
  encoding: UTF-8

schema:
  - name: cod_entrega
    type: BIGINT
    nullable: false

  - name: cod_fatura
    type: BIGINT
    nullable: false

  - name: cod_uc
    type: BIGINT
    nullable: false

  - name: cod_distribuidora
    type: INTEGER
    nullable: false

  - name: data_emissao
    type: DATE
    nullable: false

  - name: data_vencimento
    type: DATE
    nullable: false

  - name: data_entrega
    type: DATE
    nullable: true

  - name: lat_entrega
    type: DOUBLE
    nullable: true

  - name: lon_entrega
    type: DOUBLE
    nullable: true

  - name: lat_uc
    type: DOUBLE
    nullable: true

  - name: lon_uc
    type: DOUBLE
    nullable: true

  - name: flag_entregue
    type: BOOLEAN
    nullable: false

  - name: data_registro
    type: TIMESTAMP
    nullable: false

ingestion:
  strategy: incremental
  watermark_column: data_registro
  partition_by: data_emissao
  dedup_key: [cod_entrega]
```

### Contrato: Pagamentos

```yaml
source:
  name: pagamentos
  owner_tecnico: "TBD"
  owner_negocio: "TBD"
  formato: CSV

schema:
  - name: cod_pagamento
    type: BIGINT
    nullable: false

  - name: cod_fatura
    type: BIGINT
    nullable: false

  - name: cod_uc
    type: BIGINT
    nullable: false

  - name: valor_fatura
    type: DECIMAL(12,2)
    nullable: false

  - name: valor_pago
    type: DECIMAL(12,2)
    nullable: true

  - name: data_vencimento
    type: DATE
    nullable: false

  - name: data_pagamento
    type: DATE
    nullable: true

  - name: forma_pagamento
    type: STRING
    nullable: true

  - name: data_processamento
    type: TIMESTAMP
    nullable: false

ingestion:
  strategy: incremental
  watermark_column: data_processamento
  partition_by: data_vencimento
  dedup_key: [cod_pagamento]
```

---

## Diretório de Armazenamento no MinIO

```
s3://lakehouse/
├── bronze/
│   ├── notas_operacionais/
│   ├── entregas_fatura/
│   ├── pagamentos/
│   ├── leituras/
│   ├── execucoes_campo/
│   ├── devolucoes/
│   ├── cadastros/
│   │   ├── distribuidoras/
│   │   ├── uts/
│   │   ├── cos/
│   │   ├── bases/
│   │   ├── ucs/
│   │   ├── instalacoes/
│   │   └── colaboradores/
│   ├── metas/
│   ├── fechamentos/
│   └── areas_risco/
├── silver/
│   ├── notas_operacionais/
│   ├── entregas_fatura/
│   ├── pagamentos/
│   ├── leituras/
│   ├── cadastros/
│   │   └── (mesma estrutura do bronze)
│   └── metas/
├── gold/
│   ├── fato_notas_operacionais/
│   ├── fato_entrega_fatura/
│   ├── fato_efetividade/
│   ├── fato_pagamento/
│   ├── fato_entrega_vs_coord/
│   ├── fato_nao_lidos/
│   ├── fato_metas/
│   ├── dim_tempo/
│   ├── dim_distribuidora/
│   ├── dim_ut/
│   ├── dim_co/
│   ├── dim_base/
│   ├── dim_lote/
│   ├── dim_instalacao/
│   ├── dim_uc/
│   ├── dim_colaborador/
│   └── dim_risco/
├── ml/
│   ├── features/
│   │   ├── feat_atraso/
│   │   ├── feat_inadimplencia/
│   │   └── feat_metas/
│   ├── predictions/
│   │   ├── score_atraso/
│   │   ├── score_inadimplencia/
│   │   └── score_metas/
│   └── artifacts/
│       └── (modelos serializados via MLflow)
└── audit/
    ├── reconciliation_log/
    ├── quality_results/
    └── pipeline_metadata/
```

---

## Checklist de Descoberta (Fase 0)

Para cada fonte, resolver antes da implementação:

- [ ] **Acesso**: Como obter os dados? (API, banco, SFTP, arquivo manual)
- [ ] **Credenciais**: Quem autoriza e fornece acesso?
- [ ] **Owner técnico**: Quem mantém a fonte?
- [ ] **Owner de negócio**: Quem valida as regras?
- [ ] **SLA da fonte**: Quando o dado fica disponível?
- [ ] **Volume estimado**: Quantos registros por carga?
- [ ] **Schema real**: Colunas, tipos e valores reais (não documentação)
- [ ] **Encoding e formato**: UTF-8? Latin-1? Delimitador? Headers?
- [ ] **Qualidade atual**: Nulos, duplicatas, inconsistências conhecidas?
- [ ] **Histórico disponível**: Desde quando existem dados?
- [ ] **Regras de negócio implícitas**: Existem filtros, exclusões ou transformações que a fonte já aplica?
