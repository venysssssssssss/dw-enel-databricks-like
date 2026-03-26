# Estrategia de Extracao de Dados

**Versao**: 1.0
**Data**: 2026-03-26
**Objetivo**: Definir como, de onde e quando extrair cada fonte de dados necessaria para alimentar a plataforma analitica ENEL.

---

## 1. Mapa Geral de Fontes

A plataforma consome **19 fontes de dados** organizadas em 3 categorias:

| Categoria | Qtd | Estrategia Padrao | Frequencia |
|---|---|---|---|
| Cadastrais (mestres) | 9 | Snapshot | Diaria/Semanal |
| Operacionais (transacionais) | 6 | Incremental (watermark) | Diaria |
| Fechamento / Metas | 4 | Snapshot mensal | Mensal |

---

## 2. Fontes Cadastrais — Estrategia de Extracao

### 2.1 Principio

Fontes cadastrais mudam com baixa frequencia. A estrategia e **snapshot completo**: cada carga substitui a particao inteira do dia, garantindo que o estado mais recente esteja sempre disponivel.

### 2.2 Detalhamento por Fonte

#### Cadastro de Distribuidoras

| Item | Valor |
|---|---|
| **Volume estimado** | ~4 registros (ENEL SP, RJ, CE, GO) |
| **Formato esperado** | CSV delimitado por `;` |
| **Colunas-chave** | `cod_distribuidora`, `nome`, `uf`, `regiao` |
| **Frequencia** | Sob demanda (raramente muda) |
| **Metodo de obtencao** | Arquivo CSV manual ou API REST do sistema corporativo |
| **Estrategia de carga** | Snapshot — substituicao total |
| **Validacao** | NOT NULL em todas as colunas, exatamente 4 registros esperados |
| **Fallback** | Dados estaticos versionados em `data/sample/cadastro_distribuidoras.csv` |

#### Cadastro de UTs (Unidades Tecnicas)

| Item | Valor |
|---|---|
| **Volume estimado** | ~10-20 registros |
| **Formato esperado** | CSV `;` |
| **Colunas-chave** | `cod_ut`, `nome_ut`, `cod_distribuidora` |
| **Frequencia** | Semanal |
| **Metodo de obtencao** | Export do sistema corporativo ou API |
| **Estrategia** | Snapshot |
| **Validacao** | Integridade referencial com distribuidoras, NOT NULL em chaves |

#### Cadastro de COs (Centros Operacionais)

| Item | Valor |
|---|---|
| **Volume estimado** | ~20-50 registros |
| **Formato esperado** | CSV `;` |
| **Colunas-chave** | `cod_co`, `nome_co`, `cod_ut` |
| **Frequencia** | Semanal |
| **Metodo de obtencao** | Export do sistema corporativo ou API |
| **Estrategia** | Snapshot |
| **Validacao** | Integridade referencial com UTs |

#### Cadastro de Bases/Polos

| Item | Valor |
|---|---|
| **Volume estimado** | ~24-100 registros |
| **Formato esperado** | CSV `;` |
| **Colunas-chave** | `cod_base`, `nome_base`, `cod_co`, `tipo` (BASE/POLO) |
| **Frequencia** | Semanal |
| **Metodo de obtencao** | Export ou API |
| **Estrategia** | Snapshot |
| **Validacao** | Integridade referencial com COs |

#### Cadastro de UCs (Unidades Consumidoras)

| Item | Valor |
|---|---|
| **Volume estimado** | 500k-5M registros (maior cadastro) |
| **Formato esperado** | CSV `;` ou dump de banco |
| **Colunas-chave** | `cod_uc`, `cod_instalacao`, `cod_distribuidora`, `classe`, `status` |
| **Frequencia** | Diaria |
| **Metodo de obtencao** | Export incremental do banco operacional ou arquivo diferencial |
| **Estrategia** | **Hibrida** — Snapshot na carga inicial; incremental apos estabilizacao |
| **Validacao** | Unicidade de `cod_uc`, NOT NULL em chaves, valores validos em `classe` e `status` |
| **Observacao** | Volume grande exige atencao a memoria. Processar em chunks de 100k linhas no Spark |

#### Cadastro de Instalacoes

| Item | Valor |
|---|---|
| **Volume estimado** | 500k-5M registros |
| **Formato esperado** | CSV `;` ou dump de banco |
| **Colunas-chave** | `cod_instalacao`, `cod_uc`, `endereco`, `tipo`, `latitude`, `longitude` |
| **Frequencia** | Diaria |
| **Metodo de obtencao** | Export do banco operacional |
| **Estrategia** | Hibrida (mesmo padrao de UCs) |
| **Validacao** | Integridade referencial com UCs, coordenadas dentro do territorio brasileiro |

#### Cadastro de Colaboradores

| Item | Valor |
|---|---|
| **Volume estimado** | ~40-500 registros |
| **Formato esperado** | CSV `;` |
| **Colunas-chave** | `cod_colaborador`, `nome_colaborador`, `equipe`, `funcao` |
| **Frequencia** | Semanal |
| **Metodo de obtencao** | Export do RH/sistema de campo |
| **Estrategia** | Snapshot |
| **Validacao** | Unicidade de `cod_colaborador`, NOT NULL em nome |

#### Areas de Risco

| Item | Valor |
|---|---|
| **Volume estimado** | ~100-1000 poligonos |
| **Formato esperado** | Shapefile ou GeoJSON |
| **Colunas-chave** | `id_area`, `geometria`, `nivel_risco`, `ativa`, `data_atualizacao` |
| **Frequencia** | Mensal |
| **Metodo de obtencao** | Export do GIS corporativo ou arquivo manual |
| **Estrategia** | Snapshot |
| **Transformacao na ingestao** | Converter Shapefile→GeoJSON→WKT para armazenamento tabular |
| **Validacao** | Geometrias validas, todas dentro do territorio brasileiro |

#### Calendario Operacional

| Item | Valor |
|---|---|
| **Volume estimado** | ~3650 registros (10 anos) |
| **Formato esperado** | CSV gerado internamente |
| **Colunas-chave** | `data`, `dia_semana`, `flag_feriado`, `flag_dia_util`, `uf` |
| **Frequencia** | Anual (com atualizacoes pontuais) |
| **Metodo de obtencao** | Script interno `scripts/seed_dim_tempo.py` |
| **Estrategia** | Snapshot — gerado e versionado no repositorio |
| **Validacao** | Cobertura completa do periodo, feriados por UF corretos |

---

## 3. Fontes Operacionais — Estrategia de Extracao

### 3.1 Principio

Fontes transacionais tem alto volume e atualizacoes frequentes. A estrategia e **incremental por watermark**: cada carga traz apenas registros com `watermark_column > ultimo_watermark_processado`.

### 3.2 Mecanismo de Watermark

```
1. Ler ultimo watermark da tabela audit.ingestion_log
   SELECT MAX(watermark_value)
   FROM audit.ingestion_log
   WHERE source_name = '{fonte}' AND status = 'SUCCESS'

2. Extrair dados WHERE watermark_column > ultimo_watermark

3. Persistir novo watermark apos carga bem-sucedida
```

**Fallback**: Se nao houver watermark anterior (primeira carga), processar tudo (full load).

### 3.3 Detalhamento por Fonte

#### Notas Operacionais (FONTE PRINCIPAL)

| Item | Valor |
|---|---|
| **Volume estimado** | 5k-50k registros/dia; 1-10M total historico |
| **Formato esperado** | CSV `;` (encoding UTF-8) ou query em banco |
| **Colunas (22)** | `cod_nota`, `cod_uc`, `cod_instalacao`, `cod_distribuidora`, `cod_ut`, `cod_co`, `cod_base`, `cod_lote`, `tipo_servico`, `flag_impacto_faturamento`, `area_classificada_risco`, `data_criacao`, `data_prevista`, `data_execucao`, `data_fechamento`, `data_alteracao`, `status`, `cod_colaborador`, `latitude`, `longitude`, `resultado_inspecao`, `motivo_devolucao` |
| **Watermark** | `data_alteracao` (TIMESTAMP) |
| **Particao Bronze** | `data_criacao` (DATE) |
| **Deduplicacao** | Chave: `cod_nota`, Ordem: `data_alteracao DESC` |
| **Frequencia** | Diaria (06h) |
| **Metodo de obtencao** | **Opcao A**: Query SQL no banco operacional (preferida) |
| | **Opcao B**: Arquivo CSV depositado via SFTP |
| | **Opcao C**: API REST paginada |
| **Validacao** | min 100 registros/dia, NOT NULL em `cod_nota`, `cod_uc`, `status`, `data_alteracao` |
| **Testes de qualidade** | Unicidade `(cod_nota, data_alteracao)`, referential integrity com distribuidoras |

**Query de extracao (Opcao A — banco)**:
```sql
SELECT
    cod_nota, cod_uc, cod_instalacao,
    cod_distribuidora, cod_ut, cod_co, cod_base, cod_lote,
    tipo_servico, flag_impacto_faturamento, area_classificada_risco,
    data_criacao, data_prevista, data_execucao, data_fechamento,
    data_alteracao, status, cod_colaborador,
    latitude, longitude,
    resultado_inspecao, motivo_devolucao
FROM schema_operacional.notas_operacionais
WHERE data_alteracao > :ultimo_watermark
ORDER BY data_alteracao ASC
```

**Cenarios de borda**:
- Nota reaberta: `data_alteracao` atualiza, carga incremental captura automaticamente
- Nota cancelada: idem — status muda, watermark atualiza
- Retroativo: se dados passados forem corrigidos na fonte, rodar carga full pontual

#### Entregas de Fatura

| Item | Valor |
|---|---|
| **Volume estimado** | 10k-100k registros/dia |
| **Formato esperado** | CSV `;` ou query em banco |
| **Colunas (13)** | `cod_entrega`, `cod_fatura`, `cod_uc`, `cod_distribuidora`, `data_emissao`, `data_vencimento`, `data_entrega`, `lat_entrega`, `lon_entrega`, `lat_uc`, `lon_uc`, `flag_entregue`, `data_registro` |
| **Watermark** | `data_registro` (TIMESTAMP) |
| **Particao Bronze** | `data_emissao` (DATE) |
| **Deduplicacao** | Chave: `cod_entrega` |
| **Frequencia** | Diaria |
| **Metodo de obtencao** | Query SQL ou CSV via SFTP |
| **Validacao** | NOT NULL em `cod_entrega`, `cod_fatura`, `cod_uc`, `flag_entregue` |

**Query de extracao**:
```sql
SELECT
    cod_entrega, cod_fatura, cod_uc, cod_distribuidora,
    data_emissao, data_vencimento, data_entrega,
    lat_entrega, lon_entrega, lat_uc, lon_uc,
    flag_entregue, data_registro
FROM schema_operacional.entregas_fatura
WHERE data_registro > :ultimo_watermark
ORDER BY data_registro ASC
```

#### Leituras de Medidor

| Item | Valor |
|---|---|
| **Volume estimado** | 50k-200k registros/dia |
| **Formato esperado** | CSV `;` ou query em banco |
| **Colunas** | `cod_leitura`, `cod_uc`, `cod_medidor`, `data_leitura`, `leitura_kwh`, `flag_lido`, `motivo_nao_leitura`, `cod_leiturista`, `cod_rota`, `latitude`, `longitude`, `data_registro` |
| **Watermark** | `data_leitura` (TIMESTAMP) |
| **Particao Bronze** | `data_leitura` (DATE) |
| **Deduplicacao** | Chave: `cod_leitura` |
| **Frequencia** | Diaria |
| **Metodo de obtencao** | Query SQL ou CSV |
| **Validacao** | NOT NULL em `cod_leitura`, `cod_uc`, `flag_lido`; se `flag_lido=FALSE`, `motivo_nao_leitura` NOT NULL |

#### Pagamentos

| Item | Valor |
|---|---|
| **Volume estimado** | 10k-100k registros/dia |
| **Formato esperado** | CSV `;` (valores monetarios com virgula decimal: `1.234,56`) |
| **Colunas (8)** | `cod_pagamento`, `cod_fatura`, `cod_uc`, `valor_fatura`, `valor_pago`, `data_vencimento`, `data_pagamento`, `forma_pagamento`, `data_processamento` |
| **Watermark** | `data_processamento` (TIMESTAMP) |
| **Particao Bronze** | `data_vencimento` (DATE) |
| **Deduplicacao** | Chave: `cod_pagamento` |
| **Frequencia** | Diaria |
| **Metodo de obtencao** | Query SQL ou CSV via SFTP |
| **Validacao** | NOT NULL em `cod_pagamento`, `cod_fatura`, `valor_fatura`; `data_pagamento` pode ser NULL (fatura em aberto) |
| **Atencao** | Formato decimal brasileiro (virgula). Bronze preserva como STRING; conversao na Silver |

**Query de extracao**:
```sql
SELECT
    cod_pagamento, cod_fatura, cod_uc,
    valor_fatura, valor_pago,
    data_vencimento, data_pagamento,
    forma_pagamento, data_processamento
FROM schema_financeiro.pagamentos
WHERE data_processamento > :ultimo_watermark
ORDER BY data_processamento ASC
```

#### Execucoes em Campo

| Item | Valor |
|---|---|
| **Volume estimado** | 5k-30k registros/dia |
| **Formato esperado** | CSV `;` ou query |
| **Colunas** | `cod_execucao`, `cod_nota`, `cod_colaborador`, `data_execucao`, `hora_inicio`, `hora_fim`, `resultado`, `evidencia_foto`, `latitude`, `longitude`, `data_registro` |
| **Watermark** | `data_execucao` (TIMESTAMP) |
| **Particao Bronze** | `data_execucao` (DATE) |
| **Deduplicacao** | Chave: `cod_execucao` |
| **Frequencia** | Diaria |
| **Validacao** | NOT NULL em `cod_execucao`, `cod_nota`, `resultado` |
| **Observacao** | Join com notas_operacionais na Silver para enriquecer status de execucao |

#### Devolucoes de Nota

| Item | Valor |
|---|---|
| **Volume estimado** | 500-5k registros/dia |
| **Formato esperado** | CSV `;` ou query |
| **Colunas** | `cod_devolucao`, `cod_nota`, `cod_colaborador`, `data_devolucao`, `motivo_devolucao`, `observacao`, `data_registro` |
| **Watermark** | `data_devolucao` (TIMESTAMP) |
| **Particao Bronze** | `data_devolucao` (DATE) |
| **Deduplicacao** | Chave: `cod_devolucao` |
| **Frequencia** | Diaria |
| **Validacao** | NOT NULL em `cod_devolucao`, `cod_nota`, `motivo_devolucao` |
| **Observacao** | Motivo padronizado — validar contra lista de motivos conhecidos |

---

## 4. Fontes de Fechamento / Metas — Estrategia de Extracao

### 4.1 Principio

Dados de fechamento e metas sao **imutaveis apos publicacao**. Chegam uma vez por mes e a carga e snapshot particionado por mes de referencia.

### 4.2 Detalhamento por Fonte

#### Metas Operacionais

| Item | Valor |
|---|---|
| **Volume estimado** | 200-2000 registros/mes |
| **Formato esperado** | Excel (`.xlsx`) ou CSV |
| **Colunas** | `cod_distribuidora`, `cod_ut`, `cod_co`, `cod_base`, `indicador`, `mes_referencia`, `valor_meta`, `valor_realizado` |
| **Frequencia** | Mensal (ate dia 5 do mes seguinte) |
| **Metodo de obtencao** | Arquivo Excel depositado por gestor ou export do sistema de metas |
| **Estrategia** | Snapshot por `mes_referencia` |
| **Validacao** | Todas as bases devem ter meta, `valor_meta > 0`, `mes_referencia` valido |
| **Transformacao** | Se Excel: converter para CSV antes da ingestao (pandas/openpyxl) |

**Indicadores esperados**: `ENTREGA_FATURA`, `EFETIVIDADE`, `LEITURA`, `CORTE`, `RELIGACAO`, `INADIMPLENCIA`

#### Fechamento Mensal

| Item | Valor |
|---|---|
| **Volume estimado** | 500-5000 registros/mes |
| **Formato esperado** | Excel ou CSV |
| **Colunas** | `cod_distribuidora`, `cod_ut`, `cod_co`, `cod_base`, `indicador`, `mes_referencia`, `valor_realizado_final`, `valor_meta_final`, `pct_atingimento_final`, `status_meta` |
| **Frequencia** | Mensal (apos fechamento oficial) |
| **Metodo de obtencao** | Arquivo oficial publicado pela area de planejamento |
| **Estrategia** | Snapshot imutavel — uma vez inserido, **nunca sobrescreve** |
| **Validacao** | Cross-check com metas (`valor_meta_final` deve bater com `valor_meta` do mesmo mes) |
| **Regra critica** | Fechamento e a verdade final. Se divergir de calculos internos, fechamento prevalece |

#### Relatorio de Efetividade

| Item | Valor |
|---|---|
| **Volume estimado** | 1000-10000 registros/mes |
| **Formato esperado** | Excel ou CSV |
| **Colunas** | `cod_distribuidora`, `cod_ut`, `cod_co`, `cod_base`, `mes_referencia`, `total_notas`, `executadas`, `executadas_no_prazo`, `devolvidas`, `efetividade_bruta_pct`, `efetividade_liquida_pct` |
| **Frequencia** | Mensal |
| **Metodo de obtencao** | Export do sistema de gestao operacional |
| **Estrategia** | Snapshot por mes |
| **Validacao** | `efetividade_bruta >= efetividade_liquida`, `total_notas >= executadas` |

#### Comparativo Entrega vs Coordenada

| Item | Valor |
|---|---|
| **Volume estimado** | 10k-100k registros/mes |
| **Formato esperado** | CSV |
| **Colunas** | `cod_entrega`, `cod_uc`, `lat_entrega`, `lon_entrega`, `lat_uc`, `lon_uc`, `distancia_metros`, `flag_dentro_coordenada`, `tolerancia_metros`, `mes_referencia` |
| **Frequencia** | Mensal |
| **Metodo de obtencao** | Export do sistema de rastreamento ou calculo interno |
| **Estrategia** | Snapshot por mes |
| **Validacao** | Coordenadas dentro do Brasil, `distancia_metros >= 0` |

---

## 5. Protocolos de Obtencao de Dados

### 5.1 Opcao A — Query Direta em Banco (Preferida)

```
[Banco Operacional] --JDBC--> [Spark] --Iceberg--> [MinIO Bronze]
```

**Quando usar**: Quando ha acesso direto ao banco da fonte.

**Implementacao**:
```python
# Em src/ingestion/db_ingestor.py (a ser criado)
class DatabaseIngestor(BaseIngestor):
    """Extrai dados diretamente de banco via JDBC."""

    def extract(self) -> DataFrame:
        jdbc_url = self.config.source.connection_url
        query = self._build_incremental_query()

        return self.spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("query", query) \
            .option("fetchsize", "10000") \
            .option("isolationLevel", "READ_COMMITTED") \
            .load()

    def _build_incremental_query(self) -> str:
        last_wm = self._get_last_watermark()
        base_query = self.config.ingestion.extraction_query
        if last_wm:
            return f"{base_query} WHERE {self.config.ingestion.watermark_column} > '{last_wm}'"
        return base_query
```

**Requisitos**:
- Driver JDBC compativel (PostgreSQL, Oracle, SQL Server)
- Credenciais armazenadas em variavel de ambiente (nunca em codigo)
- Rede com acesso ao banco (VPN se necessario)
- Usuario com permissao READ ONLY

### 5.2 Opcao B — Arquivo CSV via SFTP/Deposito

```
[Sistema Fonte] --SFTP/NFS--> [Diretorio Raw] --Spark--> [MinIO Bronze]
```

**Quando usar**: Quando a fonte gera exports periodicos em arquivo.

**Implementacao** (ja existente em `CSVIngestor`):
```python
# Fluxo atual
1. Arquivo depositado em data/raw/{fonte}/ ou path configurado no YAML
2. CSVIngestor le o arquivo com delimitador e encoding configurados
3. IncrementalIngestor filtra por watermark
4. BaseIngestor adiciona metadados e grava no Iceberg
```

**Requisitos**:
- Path de deposito definido e acessivel
- Convencao de nomes: `{fonte}_{YYYYMMDD}.csv` ou `{fonte}_delta_{YYYYMMDD}.csv`
- Encoding: UTF-8 (converter se necessario)
- Delimitador: `;` (padrao ENEL)

### 5.3 Opcao C — API REST

```
[API Corporativa] --HTTP/JSON--> [Python] --DataFrame--> [Spark] --Iceberg--> [MinIO]
```

**Quando usar**: Quando a fonte disponibiliza API paginada.

**Implementacao**:
```python
# Em src/ingestion/api_ingestor.py (a ser criado)
class APIIngestor(BaseIngestor):
    """Extrai dados via API REST paginada."""

    def extract(self) -> DataFrame:
        all_records = []
        page = 1
        last_wm = self._get_last_watermark()

        while True:
            response = self._fetch_page(page, since=last_wm)
            if not response["data"]:
                break
            all_records.extend(response["data"])
            page += 1

        pdf = pd.DataFrame(all_records)
        return self.spark.createDataFrame(pdf)

    def _fetch_page(self, page: int, since: str | None) -> dict:
        params = {"page": page, "page_size": 1000}
        if since:
            params["updated_after"] = since
        resp = httpx.get(
            self.config.source.api_url,
            params=params,
            headers={"Authorization": f"Bearer {self._get_token()}"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
```

**Requisitos**:
- Endpoint documentado com paginacao
- Autenticacao (Bearer token ou API key)
- Rate limiting respeitado (sleep entre paginas se necessario)
- Timeout configuravel

### 5.4 Opcao D — Arquivo Excel (Metas/Fechamentos)

```
[Gestor] --Upload/Email--> [Diretorio] --pandas--> [CSV] --Spark--> [MinIO]
```

**Quando usar**: Para fontes manuais (metas, fechamentos).

**Implementacao**:
```python
# Em src/ingestion/excel_ingestor.py (a ser criado)
class ExcelIngestor(SnapshotIngestor):
    """Converte Excel para DataFrame e ingesta como snapshot."""

    def extract(self) -> DataFrame:
        import openpyxl  # lazy import

        pdf = pd.read_excel(
            self.config.source.path,
            sheet_name=self.config.source.sheet_name or 0,
            dtype=str,  # tudo como string no Bronze
        )

        # Normalizar headers
        pdf.columns = [
            col.strip().lower().replace(" ", "_")
            for col in pdf.columns
        ]

        return self.spark.createDataFrame(pdf)
```

---

## 6. Calendario de Extracao

### 6.1 Pipeline Diario (Airflow DAG: `ingestion_daily`)

```
06:00  Inicio da DAG
  |
  +-- [Paralelo] Cadastros Snapshot
  |     +-- distribuidoras
  |     +-- uts
  |     +-- cos
  |     +-- bases
  |     +-- colaboradores
  |
  +-- [Sequencial] UCs e Instalacoes (alto volume, evitar pico de memoria)
  |     +-- ucs
  |     +-- instalacoes
  |
  +-- [Paralelo] Operacionais Incrementais
  |     +-- notas_operacionais
  |     +-- entregas_fatura
  |     +-- pagamentos
  |     +-- leituras
  |     +-- execucoes_campo
  |     +-- devolucoes
  |
  +-- [Final] Auditoria e Alertas
        +-- log_summary
        +-- send_alerts (se falhas)

~06:30  Fim estimado (dados de amostra)
~07:30  Fim estimado (producao, 1M+ registros)
```

### 6.2 Pipeline Mensal (Airflow DAG: `ingestion_monthly`)

```
Dia 5 do mes, 08:00
  |
  +-- metas_operacionais
  +-- fechamento_mensal
  +-- relatorio_efetividade
  +-- comparativo_entrega_coordenada
  |
  +-- [Final] Validacao cruzada metas vs fechamento
```

### 6.3 Pipeline Sob Demanda

```
Trigger manual via Airflow UI ou CLI
  |
  +-- areas_risco (quando atualizado)
  +-- calendario_operacional (anual ou correcao)
  +-- full_reload de qualquer fonte (reprocessamento)
```

---

## 7. Tratamento de Erros e Resiliencia

### 7.1 Retry Policy

```python
default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}
```

### 7.2 Cenarios de Falha

| Cenario | Deteccao | Acao |
|---|---|---|
| Fonte indisponivel | Timeout/ConnectionError | Retry automatico (2x). Se persistir, alerta no Slack/email |
| Arquivo nao encontrado | FileNotFoundError | Alerta imediato. DAG marca task como FAILED |
| Schema inesperado | Colunas faltando na validacao | Rejeitar carga inteira. Nao gravar no Bronze |
| Volume zero | `df.count() == 0` apos watermark | Gravar log "sem novos dados", nao e erro |
| Volume anomalo | `count < min_rows` do YAML | WARNING no log. Gravar mas sinalizar alerta |
| Dados corrompidos | Encoding errado, delimitador errado | Rejeitar carga. Alerta para correcao manual |
| Watermark retroativo | Dados com `watermark < ultimo_processado` | Log de warning, processar normalmente (pode ser correcao) |

### 7.3 Dead Letter Queue

Registros que falham na validacao individual (nao toda a carga):
```
s3://lakehouse/bronze/_rejected/
  {fonte}/
    _partition_date=2026-03-25/
      rejected_records.parquet
      rejection_manifest.json  # motivo, contagem, run_id
```

### 7.4 Idempotencia

Toda carga e idempotente:
- **Snapshot**: Overwrite da particao garante que re-execucao nao duplica
- **Incremental**: Watermark garante que re-execucao nao duplica (mesmo watermark = mesmos dados)
- **Metadados**: `_run_id` diferente a cada execucao permite rastreabilidade

---

## 8. Seguranca e Credenciais

### 8.1 Principios

- **Zero credenciais em codigo**: Tudo via variavel de ambiente ou secrets manager
- **Minimo privilegio**: Usuarios de banco com READ ONLY
- **Criptografia em transito**: JDBC sobre SSL, SFTP (nunca FTP), HTTPS para APIs
- **Auditoria**: Todo acesso registrado em `audit.ingestion_log`

### 8.2 Variaveis de Ambiente Necessarias

```bash
# Banco operacional (se Opcao A)
ENEL_SOURCE_DB_HOST=
ENEL_SOURCE_DB_PORT=
ENEL_SOURCE_DB_USER=
ENEL_SOURCE_DB_PASSWORD=
ENEL_SOURCE_DB_DATABASE=
ENEL_SOURCE_DB_SCHEMA=

# SFTP (se Opcao B)
ENEL_SFTP_HOST=
ENEL_SFTP_USER=
ENEL_SFTP_KEY_PATH=

# API (se Opcao C)
ENEL_API_BASE_URL=
ENEL_API_CLIENT_ID=
ENEL_API_CLIENT_SECRET=

# Infraestrutura (ja configuradas)
ENEL_MINIO_ENDPOINT=
ENEL_MINIO_ACCESS_KEY=
ENEL_MINIO_SECRET_KEY=
ENEL_POSTGRES_HOST=
ENEL_POSTGRES_PASSWORD=
```

---

## 9. Volumetria e Limites de Hardware

### 9.1 Restricoes (16GB RAM, i7-1185G7)

| Parametro | Limite |
|---|---|
| Spark driver memory | 4GB (max durante ingestao) |
| Registros por batch | 500k (alem disso, particionar a leitura) |
| Arquivos simultaneos | 1 fonte por vez no modo sequencial do Airflow |
| Tempo max por fonte | 10 minutos (timeout no Airflow) |

### 9.2 Estrategias de Otimizacao

**Para fontes grandes (UCs, Instalacoes, Leituras)**:
```python
# Ler em chunks para controlar memoria
df = spark.read.csv(path, header=True, sep=";") \
    .repartition(8)  # shuffle.partitions = 8

# Ou via JDBC com particao
df = spark.read.format("jdbc") \
    .option("partitionColumn", "cod_distribuidora") \
    .option("lowerBound", "1") \
    .option("upperBound", "4") \
    .option("numPartitions", "4") \
    .load()
```

**Sequenciamento no Airflow**:
```
SequentialExecutor = 1 task por vez
→ Nunca mais de 1 Spark session ativa
→ Memoria previsivel e controlada
```

---

## 10. Dados de Amostra para Desenvolvimento

### 10.1 Estrategia de Amostra

Para desenvolvimento e testes, o repositorio ja contem dados sinteticos em `data/sample/`:

| Arquivo | Registros | Gerador |
|---|---|---|
| `notas_operacionais.csv` | 1000 | `src/common/sample_data.py` |
| `entregas_fatura.csv` | 1000 | idem |
| `pagamentos.csv` | 1000 | idem |
| `cadastro_distribuidoras.csv` | 4 | idem |
| `cadastro_uts.csv` | ~12 | idem |
| `cadastro_cos.csv` | ~20 | idem |
| `cadastro_bases.csv` | ~24 | idem |
| `cadastro_ucs.csv` | 500 | idem |
| `cadastro_instalacoes.csv` | 500 | idem |
| `cadastro_colaboradores.csv` | 40 | idem |
| `metas_operacionais.csv` | 24 | idem |
| `dim_tempo.csv` | ~3650 | `scripts/seed_dim_tempo.py` |

**Para gerar novamente**:
```bash
python -m scripts.generate_sample_data --rows 5000
```

### 10.2 De Amostra para Producao

A transicao de dados de amostra para dados reais exige apenas:

1. **Alterar o `path`** no YAML de configuracao de cada fonte:
   ```yaml
   # Antes (desenvolvimento)
   source:
     path: data/sample/notas_operacionais.csv

   # Depois (producao — CSV)
   source:
     path: /data/raw/notas_operacionais/notas_20260325.csv

   # Depois (producao — banco)
   source:
     type: database
     connection_url: jdbc:postgresql://host:5432/enel_prod
     extraction_query: "SELECT * FROM notas_operacionais"
   ```

2. **Ajustar credenciais** nas variaveis de ambiente
3. **Validar schema real** contra o contrato YAML (pode ter colunas extras ou nomes diferentes)
4. **Ajustar volumes** nos testes de qualidade (`min_rows`, `max_null_pct`)

---

## 11. Fase 0 — Checklist de Descoberta

Antes de conectar cada fonte real, resolver:

### Para Cada Fonte

- [ ] **Acesso confirmado**: Credenciais obtidas e testadas
- [ ] **Owner tecnico identificado**: Quem mantem a fonte?
- [ ] **Owner de negocio identificado**: Quem valida as regras?
- [ ] **SLA da fonte documentado**: Quando o dado fica disponivel?
- [ ] **Volume real medido**: Quantos registros por carga?
- [ ] **Schema real validado**: Colunas, tipos e valores reais vs documentacao
- [ ] **Encoding confirmado**: UTF-8? Latin-1? BOM?
- [ ] **Formato confirmado**: Delimitador, aspas, headers, formato de data
- [ ] **Qualidade baseline**: Nulos, duplicatas, inconsistencias conhecidas
- [ ] **Historico disponivel**: Desde quando existem dados? Backfill necessario?
- [ ] **Regras implicitas**: Filtros ou transformacoes que a fonte ja aplica?
- [ ] **Ambiente de teste**: Existe ambiente nao-produtivo para testes?

### Prioridade de Resolucao

```
P0 (Resolver primeiro — bloqueia Sprint 04):
  1. Notas Operacionais — fonte principal de toda a plataforma
  2. Entregas de Fatura — necessario para metricas de entrega
  3. Pagamentos — necessario para inadimplencia
  4. 7 Cadastros — dimensoes conformadas

P1 (Resolver em seguida — bloqueia Sprint 05):
  5. Leituras de Medidor — necessario para nao-lidos
  6. Execucoes em Campo — enriquece notas
  7. Devolucoes — enriquece notas

P2 (Resolver ate Sprint 07 — bloqueia Gold):
  8. Metas Operacionais
  9. Fechamento Mensal
  10. Relatorio de Efetividade
  11. Comparativo Entrega vs Coordenada

P3 (Resolver ate Sprint 10 — bloqueia ML):
  12. Areas de Risco (GeoJSON)
  13. Calendario Operacional (ja resolvido — gerado internamente)
```

---

## 12. Fluxo de Dados Completo — Visao End-to-End

```
                    FONTES EXTERNAS
                         |
    +--------------------+--------------------+
    |                    |                    |
  [Banco]            [SFTP/CSV]          [API REST]
    |                    |                    |
    v                    v                    v
  DatabaseIngestor   CSVIngestor         APIIngestor
    |                    |                    |
    +--------------------+--------------------+
                         |
                   BaseIngestor
                    (template)
                         |
              +----------+----------+
              |                     |
        IncrementalIngestor   SnapshotIngestor
        (watermark filter)    (partition replace)
              |                     |
              +----------+----------+
                         |
                  add_technical_metadata()
                  (_run_id, _ingested_at,
                   _source_hash, _partition_date)
                         |
                  write_bronze()
                  (Iceberg/MinIO)
                         |
                  audit()
                  (audit.ingestion_log)
                         |
                   BRONZE LAYER
                   (19 tabelas)
                         |
                    [Silver...]
                    [Gold...]
                    [ML...]
```

---

## 13. Metricas de Monitoramento da Extracao

### Dashboard de Ingestao (Grafana)

| Metrica | Query | Alerta |
|---|---|---|
| Ingestoes/dia por fonte | `COUNT(*) FROM audit.ingestion_log WHERE date = today GROUP BY source` | < 1 para fonte diaria |
| Volume ingerido | `SUM(rows_ingested) WHERE date = today` | Desvio > 50% da media 7d |
| Taxa de sucesso | `COUNT(status='SUCCESS') / COUNT(*)` | < 100% |
| Duracao media | `AVG(duration_seconds) GROUP BY source` | > 600s (10min) |
| Freshness | `MAX(executed_at) por fonte` | > 24h para fonte diaria |
| Watermark gap | `MAX(watermark) - now()` | > 48h |

### Alertas Criticos

```yaml
alerts:
  - name: ingestion_failure
    condition: "status = 'FAILURE' para qualquer fonte P0"
    action: "Notificar equipe imediatamente"
    channel: slack/email

  - name: volume_anomaly
    condition: "rows_ingested < 10% da media_7d"
    action: "Notificar para investigacao"

  - name: freshness_breach
    condition: "ultima_ingestao > 24h para fonte diaria"
    action: "Trigger manual + investigacao"
```
