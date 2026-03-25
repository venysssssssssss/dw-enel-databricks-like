# Sprint 01 — Discovery & Project Setup

**Fase**: 0 — Descoberta
**Duração**: 2 semanas
**Objetivo**: Estruturar o projeto, mapear fontes de dados reais, validar glossário de negócio e preparar o repositório para desenvolvimento.

---

## Backlog da Sprint

### US-001: Setup do Repositório Git
**Prioridade**: P0 (bloqueante)
**Story Points**: 3

**Tarefas**:
1. Inicializar repositório Git
2. Criar estrutura de diretórios do projeto:
   ```
   dw-enel-databricks-like/
   ├── src/
   │   ├── ingestion/          # Jobs de ingestão Bronze
   │   │   ├── __init__.py
   │   │   ├── base.py         # Classe base de ingestão
   │   │   ├── csv_ingestor.py
   │   │   ├── db_ingestor.py
   │   │   └── config/         # YAML configs por fonte
   │   ├── transformation/     # Jobs Silver
   │   │   ├── __init__.py
   │   │   ├── base.py
   │   │   └── processors/
   │   ├── api/                # FastAPI
   │   │   ├── main.py
   │   │   ├── config.py
   │   │   ├── routers/
   │   │   ├── schemas/
   │   │   ├── services/
   │   │   ├── infrastructure/
   │   │   └── auth/
   │   ├── ml/                 # Machine Learning
   │   │   ├── __init__.py
   │   │   ├── features/
   │   │   ├── models/
   │   │   ├── scoring/
   │   │   └── monitoring/
   │   ├── quality/            # Great Expectations
   │   │   ├── expectations/
   │   │   └── checkpoints/
   │   └── common/             # Utilitários compartilhados
   │       ├── __init__.py
   │       ├── spark_session.py
   │       ├── minio_client.py
   │       ├── logging.py
   │       └── config.py
   ├── dbt/                    # dbt project (Gold layer)
   │   ├── dbt_project.yml
   │   ├── models/
   │   │   ├── staging/
   │   │   ├── marts/
   │   │   └── dimensions/
   │   ├── tests/
   │   ├── macros/
   │   └── seeds/
   ├── airflow/                # DAGs
   │   ├── dags/
   │   │   ├── dag_ingestion.py
   │   │   ├── dag_transformation.py
   │   │   ├── dag_dbt.py
   │   │   ├── dag_quality.py
   │   │   ├── dag_ml_features.py
   │   │   ├── dag_ml_scoring.py
   │   │   └── dag_ml_monitoring.py
   │   └── plugins/
   ├── infra/                  # Docker & config
   │   ├── docker-compose.yml
   │   ├── docker-compose.dev.yml
   │   ├── docker-compose.ml.yml
   │   ├── docker-compose.full.yml
   │   ├── dockerfiles/
   │   │   ├── Dockerfile.spark
   │   │   ├── Dockerfile.api
   │   │   └── Dockerfile.airflow
   │   └── config/
   │       ├── trino/
   │       ├── airflow/
   │       ├── prometheus/
   │       └── grafana/
   ├── tests/
   │   ├── unit/
   │   ├── integration/
   │   └── conftest.py
   ├── docs/                   # Documentação (já criada)
   ├── scripts/                # Scripts auxiliares
   │   ├── setup_minio_buckets.py
   │   ├── seed_dim_tempo.py
   │   └── generate_sample_data.py
   ├── pyproject.toml
   ├── .env.example
   ├── .gitignore
   ├── Makefile
   ├── CLAUDE.md
   └── README.md
   ```
3. Configurar `pyproject.toml` com dependências e ferramentas (ruff, pytest, mypy)
4. Criar `.gitignore` adequado (Python, Spark, data files)
5. Criar `.env.example` com todas as variáveis necessárias
6. Criar `Makefile` com comandos de desenvolvimento

**Critério de aceite**:
- `git clone` + `make setup` funciona em máquina limpa
- Estrutura de diretórios completa com `__init__.py`
- Linting (`ruff check`) passa sem erros

---

### US-002: Configuração de Ferramentas de Desenvolvimento
**Prioridade**: P0
**Story Points**: 2

**Tarefas**:
1. Configurar `pyproject.toml`:
   ```toml
   [project]
   name = "dw-enel-databricks-like"
   version = "0.1.0"
   requires-python = ">=3.12"

   [tool.ruff]
   target-version = "py312"
   line-length = 100

   [tool.ruff.lint]
   select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "TCH"]

   [tool.pytest.ini_options]
   testpaths = ["tests"]
   asyncio_mode = "auto"

   [tool.mypy]
   python_version = "3.12"
   strict = true
   ```
2. Configurar pre-commit hooks (ruff, mypy)
3. Criar `Makefile`:
   ```makefile
   .PHONY: setup dev test lint format

   setup:
       python -m venv .venv
       .venv/bin/pip install -e ".[dev]"
       pre-commit install

   dev:
       docker compose -f infra/docker-compose.dev.yml up -d

   dev-down:
       docker compose -f infra/docker-compose.dev.yml down

   test:
       pytest tests/ -v

   test-unit:
       pytest tests/unit/ -v

   test-integration:
       pytest tests/integration/ -v

   lint:
       ruff check src/ tests/
       mypy src/

   format:
       ruff format src/ tests/
   ```

**Critério de aceite**:
- `make setup` cria ambiente virtual e instala dependências
- `make lint` executa sem erros no código base
- `make test` executa (mesmo que com 0 testes)

---

### US-003: Mapeamento de Fontes de Dados Reais
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:
1. Para cada fonte do inventário (ver `docs/business-rules/04-data-sources.md`):
   - Identificar como obter os dados (API, DB, SFTP, manual)
   - Obter amostra real de dados (5-10 registros)
   - Validar schema real vs schema documentado
   - Identificar encoding, delimitador, formato de datas
   - Documentar anomalias e edge cases encontrados
2. Criar arquivo YAML de configuração por fonte:
   ```yaml
   # src/ingestion/config/notas_operacionais.yml
   source:
     name: notas_operacionais
     type: csv  # csv | database | api
     path: "/data/raw/notas/"  # ou connection string
     encoding: utf-8
     delimiter: ";"
     date_format: "dd/MM/yyyy"
     has_header: true

   schema:
     columns:
       - name: cod_nota
         source_name: "Código Nota"  # nome real na fonte
         type: bigint
         nullable: false
       # ... todas as colunas

   ingestion:
     strategy: incremental
     watermark_column: data_alteracao
     partition_by: data_criacao
     dedup_key: [cod_nota]

   quality:
     min_rows: 100
     max_null_pct: 0.05
   ```
3. Atualizar documentação com descobertas

**Critério de aceite**:
- YAML de configuração para pelo menos 5 fontes prioritárias
- Amostra de dados reais obtida e validada
- Divergências schema documentado vs real documentadas

---

### US-004: Validação do Glossário Operacional
**Prioridade**: P1
**Story Points**: 5

**Tarefas**:
1. Revisar glossário (`docs/business-rules/01-business-glossary.md`) com stakeholder de negócio
2. Para cada regra de negócio:
   - Confirmar que a fórmula está correta
   - Confirmar valores permitidos (ACF tipos, status, etc.)
   - Confirmar exceções e edge cases
   - Documentar regras que variam por distribuidora
3. Validar com dados reais:
   - Aplicar regras de classificação ACF/ASF nos dados de amostra
   - Comparar resultado com classificação existente
   - Documentar divergências
4. Formalizar documento de aprovação com owner de negócio

**Critério de aceite**:
- Glossário revisado e aprovado pelo negócio
- Regras que variam por distribuidora identificadas e documentadas
- Pelo menos 1 exemplo real validado por regra

---

### US-005: Geração de Dados de Amostra para Desenvolvimento
**Prioridade**: P1
**Story Points**: 5

**Tarefas**:
1. Criar script `scripts/generate_sample_data.py`:
   - Gera dados sintéticos realistas para todas as fontes
   - Respeita schemas e regras de negócio
   - Inclui edge cases intencionais (nulos, duplicatas, datas inválidas)
   - Volume: ~10k registros por fonte
2. Gerar datasets de amostra:
   - `data/sample/notas_operacionais.csv`
   - `data/sample/entregas_fatura.csv`
   - `data/sample/pagamentos.csv`
   - `data/sample/cadastro_distribuidoras.csv`
   - `data/sample/cadastro_uts.csv`
   - `data/sample/cadastro_cos.csv`
   - `data/sample/cadastro_bases.csv`
   - `data/sample/cadastro_ucs.csv`
   - `data/sample/metas_operacionais.csv`
3. Criar script de seed da `dim_tempo` (`scripts/seed_dim_tempo.py`):
   - Gerar dimensão tempo de 2020 a 2030
   - Incluir feriados nacionais e estaduais (CE, SP, RJ, GO)
   - Flags de dia útil por distribuidora/UF

**Critério de aceite**:
- `python scripts/generate_sample_data.py` gera todos os CSVs
- Dados passam nas validações de schema documentadas
- Dados incluem cenários de edge case documentados

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| Repositório Git estruturado | |
| pyproject.toml + Makefile configurados | |
| YAMLs de configuração de fontes (≥5) | |
| Glossário validado com negócio | |
| Dados de amostra para desenvolvimento | |
| Script de seed dim_tempo | |

## Riscos da Sprint

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Stakeholder não disponível para validar glossário | Alta | Médio | Agendar reunião na Sprint Planning |
| Formato real dos dados muito diferente do documentado | Média | Alto | Começar mapeamento no dia 1 |
| Amostra de dados reais não disponível | Média | Alto | Usar dados sintéticos e validar depois |
