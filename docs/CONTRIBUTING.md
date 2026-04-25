# Contributing

Guia de contribuição para `dw-enel-databricks-like`. Seções marcadas como `AUTO-GENERATED` são derivadas de fontes de verdade (`Makefile`, `pyproject.toml`, `.env.example`) — **não editar manualmente**.

## Pré-requisitos

- Python 3.12+
- Docker + Docker Compose plugin
- 16GB RAM recomendado (stack local é CPU-only)
- `make`

## Setup de desenvolvimento

```bash
cp .env.example .env
make setup           # venv mínimo (dev extras)
# ou
make setup-all       # venv com todos os extras (dev, api, ml, platform, viz)
```

Pré-commit hooks (ruff, mypy) são instalados automaticamente pelo target `setup`.

## Comandos disponíveis

<!-- AUTO-GENERATED:MAKE-TARGETS -->
| Comando | Descrição |
|---------|-----------|
| `make setup` | Cria venv e instala dependências `dev` + pre-commit |
| `make setup-all` | Cria venv e instala todos os extras (`dev,api,ml,platform,viz`) |
| `make dev` | Sobe perfil dev (MinIO, Spark, Trino, Airflow, Nessie, Postgres) |
| `make full` | Sobe stack completa (dev + Superset + Grafana + Prometheus) |
| `make ml` | Sobe perfil ML (MLflow + dependências) |
| `make down` | Derruba stack dev com `--remove-orphans` |
| `make test` | Executa toda a suíte `pytest tests/ -v` |
| `make test-unit` | Executa apenas `tests/unit/` |
| `make test-integration` | Executa apenas `tests/integration/` |
| `make lint` | Roda `ruff check` + `mypy` em `src/ tests/ scripts/` |
| `make format` | Roda `ruff format` em `src/ tests/ scripts/` |
| `make pipeline` | Gera dados sintéticos (`scripts.generate_sample_data`) |
| `make smoke` | Seed mínimo de `dim_tempo` |
| `make sample-data` | Gera 1000 linhas de dados sintéticos |
| `make seed-time` | Gera CSV `dim_tempo` em `data/sample/` |
| `make features` | Materializa features para `2026-03-01` |
| `make train` | Treina modelos com `test-date=2026-03-01` |
| `make score` | Executa scoring batch em `2026-03-01` |
| `make drift` | Checa drift do modelo `atraso_entrega` |
| `make erro-leitura-dry-run` | Dry-run do ingestor Sprint 13 sobre `DESCRICOES_ENEL/` |
| `make erro-leitura-normalize` | Normaliza Silver (erro de leitura) |
| `make erro-leitura-train` | Treina classificador de erro de leitura |
| `make erro-leitura-dashboard` | Sobe Streamlit local do dashboard |
| `make share-up` | Sobe stack de compartilhamento público (Streamlit + Caddy + Cloudflared) |
| `make share-url` | Reimprime URL pública do tunnel ativo |
| `make share-logs` | Stream de logs da stack de compartilhamento |
| `make share-down` | Derruba stack de compartilhamento |
<!-- /AUTO-GENERATED:MAKE-TARGETS -->

## Extras de dependência

<!-- AUTO-GENERATED:EXTRAS -->
| Extra | Propósito | Pacotes principais |
|-------|-----------|--------------------|
| `dev` | Qualidade de código e testes | `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-cov`, `pre-commit` |
| `platform` | Lakehouse runtime | `apache-airflow`, `pyspark`, `trino[sqlalchemy]`, `great-expectations` |
| `ml` | Modelagem e NLP | `lightgbm`, `xgboost`, `scikit-learn`, `mlflow`, `bertopic`, `hdbscan`, `umap-learn`, `sentence-transformers`, `shap`, `pandas`, `numpy` |
| `api` | FastAPI | `fastapi`, `uvicorn[standard]`, `python-jose[cryptography]`, `passlib[bcrypt]`, `slowapi`, `prometheus-fastapi-instrumentator` |
| `viz` | Dashboards | `streamlit`, `plotly` |
<!-- /AUTO-GENERATED:EXTRAS -->

## Testes

- **Unit**: `make test-unit` — sem dependências externas, usa fixtures em `tests/unit/`.
- **Integration**: `make test-integration` — exige stack `make dev` rodando (MinIO, Trino, Postgres).
- **Cobertura mínima**: 80% em módulos novos (`pytest-cov` configurado em `pyproject.toml`).
- **Validação temporal**: nunca usar `train_test_split` aleatório em modelos ML. Use `TimeSeriesSplit` (ver `src/ml/models/`).

## Estilo de código

- `ruff` com `target-version = "py312"`, `line-length = 100`.
- `mypy --strict` obrigatório (`warn_return_any`, `warn_unused_configs`).
- Regras ativas: `E, F, I, N, W, UP, B, SIM, TCH`.
- Pre-commit bloqueia commit se lint/format falhar.

## Fluxo de PR

1. Branch a partir de `main`: `feat/sprint-XX-descricao` ou `fix/...`.
2. Commits seguem convenção `tipo(escopo): descrição` (ver `git log`).
3. `make lint && make test` verde antes de abrir PR.
4. PR descreve: mudança, motivação, testes executados, impacto operacional.
5. Sprints novas exigem doc em `docs/sprints/sprint-XX-*.md`.

## Convenções de arquitetura

- **Medallion estrito**: Bronze (raw + metadata) → Silver (normalizado, dedup) → Gold (dbt, dimensional).
- **Regras de negócio** vivem em pipelines e modelos dbt, **nunca** em dashboards.
- **Reuso obrigatório**: `BaseIngestor`, `BaseSilverTransformer`, `BaseModelTrainer` — não recriar o template method.
- **Metadados técnicos** em todo Bronze: `_run_id`, `_ingested_at`, `_source_hash`, `_partition_date`.
- **Open-source only**: zero dependência de serviços pagos ou vendor-locked.

## Adicionando uma nova view de aggregation

Toda tela analítica do front consome `/v1/aggregations/{view_id}`. Visões são registradas em `src/data_plane/views.py::VIEW_REGISTRY` via `ViewSpec(id, group_keys, metrics, filters_schema, handler, kwargs={})`.

Padrão canônico de view parametrizada — exemplo da família **`sp_severidade_*`** (Sprint 24):

```python
"sp_severidade_alta_overview": ViewSpec(
    "sp_severidade_alta_overview",
    (),
    ("total", "procedentes", "improcedentes", "valor_medio_fatura"),
    FILTER_FIELDS,
    sp_severidade_overview,
    {"severidade": "high"},
),
```

Checklist obrigatório ao criar uma view:

1. Implementar handler em `src/viz/<dominio>_dashboard_data.py`. Sempre retornar `pd.DataFrame` com colunas estáveis (mesmo no caso vazio).
2. Registrar no `VIEW_REGISTRY` com `group_keys`, `metrics`, e `kwargs` quando houver variantes.
3. Cobrir com pytest: caso vazio, kwargs alternativos, filtro regional, valores de borda. Ver `tests/unit/test_sp_severidade_views.py` como referência.
4. Documentar em `docs/api/aggregations.md` na tabela apropriada.
5. (Opcional) Painel Grafana em `infra/config/grafana/dashboards/` se justificar observabilidade dedicada.

**Source of truth**: derivações de severidade, categoria e peso vêm sempre de `taxonomy_metadata()` em `src/ml/models/erro_leitura_classifier.py`. Maps hard-coded em handlers ou no front são proibidos.

Referência completa do contrato e endpoints disponíveis: `docs/api/aggregations.md`.
