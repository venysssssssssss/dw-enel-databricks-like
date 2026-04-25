# Runbook Operacional

Procedimentos de operação, deploy e troubleshooting da plataforma.

## Stack e perfis Docker

<!-- AUTO-GENERATED:DOCKER-PROFILES -->
| Perfil | Arquivo | Serviços | Comando |
|--------|---------|----------|---------|
| `dev` | `infra/docker-compose.dev.yml` | MinIO, Spark, Trino, Airflow, Nessie, Postgres | `make dev` |
| `full` | `infra/docker-compose.full.yml` | `dev` + Superset + Grafana + Prometheus | `make full` |
| `ml` | `infra/docker-compose.ml.yml` | MLflow + dependências de treino | `make ml` |
| `share` | `infra/docker-compose.share.yml` | Streamlit + Caddy + Cloudflared (exposição pública) | `make share-up` |
<!-- /AUTO-GENERATED:DOCKER-PROFILES -->

## Bootstrap inicial

```bash
cp .env.example .env          # ajuste credenciais
make setup-all                # venv com todos extras
make dev                      # stack lakehouse
python -m scripts.setup_minio_buckets
python -m scripts.setup_mlflow
make sample-data              # dados sintéticos
make features                 # feature store
make train                    # modelos
```

## Health checks

| Serviço | Endpoint | HTTP 200 esperado |
|---------|----------|-------------------|
| MinIO | `http://localhost:9000/minio/health/live` | healthy |
| Trino | `http://localhost:8080/v1/status` | estado ACTIVE |
| Airflow | `http://localhost:8081/health` | `{"metadatabase":"healthy","scheduler":"healthy"}` |
| MLflow | `http://localhost:5000/health` | OK |
| Nessie | `http://localhost:19120/api/v2/config` | 200 |
| Streamlit (share) | `http://localhost:8080/_stcore/health` | OK |

## Orquestração Airflow

<!-- AUTO-GENERATED:DAGS -->
| DAG | Arquivo | Propósito |
|-----|---------|-----------|
| `dag_ingestion` | `airflow/dags/dag_ingestion.py` | Ingestão Bronze (CSVs, xlsx incremental) |
| `dag_transformation` | `airflow/dags/dag_transformation.py` | Bronze → Silver (normalização, dedup) |
| `dag_quality` | `airflow/dags/dag_quality.py` | Great Expectations checkpoints |
| `dag_dbt` | `airflow/dags/dag_dbt.py` | dbt run/test dos marts Gold |
| `dag_ml_features` | `airflow/dags/dag_ml_features.py` | Materialização de features |
| `dag_ml_training` | `airflow/dags/dag_ml_training.py` | Treino dos modelos preditivos |
| `dag_ml_scoring` | `airflow/dags/dag_ml_scoring.py` | Scoring batch |
| `dag_ml_monitoring` | `airflow/dags/dag_ml_monitoring.py` | Drift + métricas operacionais |
| `dag_erro_leitura` | `airflow/dags/dag_erro_leitura.py` | Pipeline Sprint 13: ingest→silver→topic→classifier |
| `dag_test_pipeline` | `airflow/dags/dag_test_pipeline.py` | Smoke diário end-to-end |
<!-- /AUTO-GENERATED:DAGS -->

## FastAPI — Endpoints v1

<!-- AUTO-GENERATED:API-ROUTERS -->
| Router | Arquivo | Responsabilidade |
|--------|---------|------------------|
| `health` | `src/api/routers/v1/health.py` | Liveness/readiness |
| `admin` | `src/api/routers/v1/admin.py` | Operações administrativas |
| `metrics` | `src/api/routers/v1/metrics.py` | Métricas Prometheus |
| `exports` | `src/api/routers/v1/exports.py` | Exports batch para bucket `exports` |
| `scores` | `src/api/routers/v1/scores.py` | Consulta de scores preditivos |
| `erro_leitura` | `src/api/routers/v1/erro_leitura.py` | Sprint 13: classificar/padroes/hotspots |
<!-- /AUTO-GENERATED:API-ROUTERS -->

Documentação OpenAPI: `http://localhost:8000/docs` (desenvolvimento).

## Procedimentos de deploy

### Promoção dev → staging

1. `make lint && make test` verde em CI.
2. Tag semver: `git tag vX.Y.Z && git push --tags`.
3. Atualizar `.env` do ambiente alvo (trocar todos `replace-me`).
4. Deploy via `docker compose -f infra/docker-compose.full.yml up -d`.
5. Rodar migrações dbt: `poetry run dbt run --target staging --select marts`.
6. Smoke: `make smoke`.

### Rollback

- **Iceberg**: usar Nessie branches — `nessie branch create rollback main@<commit-sha-anterior>` e re-aponte Trino.
- **dbt**: `dbt run --target prod --full-refresh --select <model>` a partir de commit anterior.
- **ML**: promover versão anterior no MLflow Registry (`models:/<name>/Production`).

### Retreino ad-hoc

```bash
make train                   # treino completo
make score                   # scoring subsequente
make drift                   # verificação de drift
```

## Compartilhamento público do dashboard

Stack dedicada em `infra/docker-compose.share.yml` (Streamlit + Caddy + Cloudflared). Ver `docs/SHARE_DASHBOARD.md` para detalhes.

```bash
make share-up        # sobe e imprime URL pública trycloudflare.com
make share-url       # reimprime URL
make share-logs      # stream logs
make share-down      # derruba
```

## Troubleshooting

| Sintoma | Diagnóstico | Fix |
|---------|-------------|-----|
| Airflow webserver não inicia | `AIRFLOW_FERNET_KEY=replace-me` | Gerar chave real e reiniciar |
| Trino retorna `No nodes available` | Coordenador subiu antes do metastore | `docker compose restart trino` |
| MLflow logging falha silenciosamente | `ENEL_MLFLOW_TRACKING_ENABLED=false` | Setar `true` no `.env` |
| Dashboard público 502 | Streamlit em cold start (pip install em runtime) | Usar imagem pré-buildada (já é o default); `make share-logs` para verificar health |
| `make test-integration` falha com timeout MinIO | Stack dev não rodando | `make dev` e aguardar health |
| Drift check retorna vazio | Referência sem artefatos | Rodar `make features && make train` antes |
| `bertopic` OOM | Dataset > 30k docs em 16GB | Reduzir batch de embeddings para 16 ou amostrar |

## Monitoração

- **Grafana**: `http://localhost:3000` (perfil `full`) — dashboards de pipeline/ML/API.
- **Prometheus**: `http://localhost:9090` — métricas raw.
- **MLflow UI**: `http://localhost:5000` — experimentos, modelos, runs.

## Incidentes frequentes

### Pipeline erro_leitura falha no embedding

Causa típica: modelo `sentence-transformers` não baixou (rede bloqueada).

Fix: pré-baixar para cache local:
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

### Iceberg compact acumula snapshots

Rodar manualmente por schema:
```sql
ALTER TABLE iceberg.bronze.<tabela> EXECUTE expire_snapshots(retention_threshold => '7d');
ALTER TABLE iceberg.bronze.<tabela> EXECUTE remove_orphan_files;
```

### Superset dashboard não atualiza

Invalidar cache: UI → Settings → Clear cache. Ou via API: `POST /api/v1/dataset/<id>/refresh`.

## Severidade SP (Sprint 24+)

### Alerta `SeveridadeCacheDegraded`

Cache miss > 80% sustentado por 10 min em alguma view `sp_severidade_*`.

Causas prováveis:
1. **Reingestão recente**: `dataset_hash` mudou e o cache em memória foi descartado. Esperar 5–10 min para re-aquecer; alerta deve resolver sozinho.
2. **TTL muito curto**: tráfego de baixa frequência mata o cache antes do hit. Avaliar aumentar `MemoryResponseCache(ttl_seconds=…)` em `src/api/routers/dashboard.py` se padrão recorrente.
3. **Filtros de alta cardinalidade**: front passando `?filters=` com combinações distintas a cada chamada (bug). Inspecionar Sentry / network panel — chave do cache inclui filtros.
4. **API restart**: cache em memória zera. Nada a fazer.

Diagnóstico:
```bash
curl -s http://api/metrics | grep enel_cache_events_total
```
Se `result="hit"` ≈ 0 e `result="miss"` crescente para o mesmo `view_id="sp_severidade_*"`, cache nunca está aquecendo.

Métricas úteis:
```promql
sum by (view_id, result) (increase(enel_cache_events_total{view_id=~"sp_severidade_.*"}[10m]))
sum(enel_severity_sp_total)
```

### Alerta `SeveridadeLatencyP95High`

p95 > 250 ms por 10 min. Investigar:
1. `python -m scripts.smoke_sp_severidade --view <view_id>` localmente para isolar handler.
2. Inspeccionar `enel_aggregation_latency_seconds_bucket{view_id=...}` por buckets para ver se cauda começa a partir de N segundos.
3. Verificar tamanho do silver: `wc -l data/silver/erro_leitura_normalizado.csv`. Se cresceu muito desde o último deploy, considerar mover handlers para Polars ou pre-agregação Iceberg.

### Página /bi/severidade-* mostra `0` em todos os KPIs

Esperado se silver SP ainda não popula `flag_resolvido_com_refaturamento`. Confirmar via:
```bash
.venv/bin/python -c "import pandas as pd; print(pd.read_csv('data/silver/erro_leitura_normalizado.csv', usecols=['_source_region','flag_resolvido_com_refaturamento']).query('_source_region == \"SP\"')['flag_resolvido_com_refaturamento'].value_counts())"
```
Se 100% `False`, é dívida da ingestão (Sprint 5/6) — não é regressão da Sprint 24.

### Rota /bi/severidade-* renderiza vazio

1. Conferir `/v1/dataset/version` retorna `hash` válido (não `pending`).
2. `curl /v1/aggregations/sp_severidade_alta_overview` retorna 200 com `data: [{...}]`.
3. Inspecionar console do navegador: `dataset_hash` na chave do React Query precisa estar populado.
4. Se backend OK mas UI vazia: verificar que o build mais recente foi servido (sem cache antigo do nginx).

### Desativar feature Severidade V1 temporariamente

Se a navegação de severidade precisar sair do ar sem rollback do build:

```bash
VITE_FEATURE_SEVERIDADE_V1=false pnpm --dir apps/web build
```

Esse flag remove as rotas `/bi/severidade-alta` e `/bi/severidade-critica` do router e oculta os links da sidebar no build resultante.

## Classifier coverage (Sprint 25+)

### Alerta `ClassifierIndefinidoSpike`

`enel_classifier_indefinido_ratio{regiao=...}` ficou acima de 40% por 24 h.

Diagnóstico rápido:
```bash
curl -s http://api:8000/v1/aggregations/classifier_coverage
curl -s http://api:8000/v1/aggregations/classifier_indefinido_tokens
```

Ações:
1. Confirmar se houve reingestão ou mudança de distribuição no silver.
2. Rodar `poetry run python scripts/relabel_erro_leitura.py --report --benchmark --sample-size 10000` para medir cobertura v3 localmente.
3. Auditar `classifier_indefinido_tokens`; se tokens recorrentes tiverem semântica operacional estável, abrir mudança de taxonomia v4.
4. Se o aumento vier de topics novos, atualizar `data/model_registry/erro_leitura/topic_to_canonical.csv` depois de validar `topic_taxonomy.json`.

### Alerta `ClassifierMetricStale`

A métrica de cobertura só é atualizada quando a view `classifier_coverage` é consultada. Se o alerta disparar:

1. Abrir o dashboard Grafana `ENEL · Classifier Coverage`.
2. Verificar se o job de warmup chama `/v1/aggregations/classifier_coverage`.
3. Confirmar que a API expõe `/metrics` e que Prometheus está lendo `alerts/*.yml`.

### Backfill v3

Para gerar colunas paralelas sem sobrescrever o silver:
```bash
poetry run python scripts/relabel_erro_leitura.py --report --benchmark
```

Para cutover controlado, use `--in-place` somente depois de validação humana documentada em `docs/business-rules/taxonomia-v3-validation.md`.
