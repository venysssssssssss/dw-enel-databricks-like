# Aggregation Endpoints (`/v1/aggregations/{view_id}`)

Reference for the unified data plane that powers the React BI surfaces.

- **Base path**: `/v1/aggregations/{view_id}`
- **Response shape**:
  ```json
  {
    "view_id": "string",
    "dataset_hash": "string (sha256 of dataset version)",
    "filters": { "regiao": ["SP"], "...": "echo of effective filters" },
    "data": [ { "...": "row" } ]
  }
  ```
- **Caching**: `ETag` + `Cache-Control: max-age=60, stale-while-revalidate=300`. Server-side memory cache TTL = 300 s, keyed by `(view_id, dataset_hash, filters)`.
- **Observability**: cache events include labels `layer`, `route`, `result`, `view_id`; aggregation latency includes `view_id` and `cache_result`.
- **Filtering**: query string `?filters=<base64url(json)>`. Whitelisted keys: `regiao`, `tipo_origem`, `causa_canonica`, `causa_canonica_confidence`, `topic_name`, `status`, `assunto`, `start_date`, `end_date`.
- **Versioning**: clients must call `/v1/dataset/version` first, then forward `dataset_hash` to all downstream calls (used to short-circuit cache).

## Authoring a new view

A view is a triple `(handler, group_keys, kwargs)` registered in `src/data_plane/views.py::VIEW_REGISTRY` via `ViewSpec`.

The canonical example with `kwargs` is the **`sp_severidade_*`** family — single handler implementation specialised by severity through registration metadata.

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

Rules of thumb:
- **Single responsibility per handler**. Branching on a kwarg is fine; branching on a string literal is a smell.
- **Source of truth for derived columns** (severidade, categoria, peso) is `taxonomy_metadata()`. Never hard-code maps in views.
- **Always return a `pd.DataFrame`** with stable column ordering. Empty input → empty frame with the same columns.

## Registry — current views

### MIS / executivo

| view_id | group_keys | metrics | notes |
|---|---|---|---|
| `mis` | `("regiao",)` | `*` | alias for `mis_executive_summary` |
| `mis_executive_summary` | `("regiao",)` | `*` | one row per region |
| `mis_monthly_mis` | `("mes_ingresso", "regiao")` | `qtd_erros, mom` | adds 3-month moving average |
| `severity_heatmap` | `("regiao", "severidade")` | `qtd_erros` | for global heatmap |
| `category_breakdown` | `("categoria", "regiao")` | `qtd_erros` | taxonomy categoria |
| `reincidence_matrix` | `("regiao", "faixa")` | `qtd_instalacoes` | 1, 2, 3-4, 5-9, 10+ ord. |
| `taxonomy_reference` | `("Categoria",)` | `Peso` | static taxonomy v2 |
| `classifier_coverage` | `("regiao", "causa_canonica_confidence")` | `qtd_ordens, percentual, indefinido_pct` | taxonomy v3 coverage by confidence |
| `classifier_indefinido_tokens` | `("token",)` | `qtd_ocorrencias` | safe audit tokens for residual `indefinido` |

### Severidade SP — Sprint 24

<!-- AUTO-GENERATED:SP-SEVERIDADE -->
| view_id | severidade | group_keys | metrics | output cardinality |
|---|---|---|---|---|
| `sp_severidade_alta_overview` | `high` | `()` | `total, procedentes, improcedentes, pct_procedentes, reincidentes_clientes, valor_medio_fatura, categorias_count, top3_share, delta_trimestre` | 1 row |
| `sp_severidade_critica_overview` | `critical` | `()` | (same) | 1 row |
| `sp_severidade_alta_mensal` | `high` | `("mes_ingresso",)` | `qtd_erros, procedentes, improcedentes` | up to 12 rows |
| `sp_severidade_critica_mensal` | `critical` | `("mes_ingresso",)` | (same) | up to 12 rows |
| `sp_severidade_alta_categorias` | `high` | `("categoria",)` | `vol, pct` (+ collapsed `outros`) | top-12 |
| `sp_severidade_critica_categorias` | `critical` | `("categoria",)` | (same) | top-12 |
| `sp_severidade_alta_causas` | `high` | `("nome",)` | `vol, proc, reinc, cat` | top-14 |
| `sp_severidade_critica_causas` | `critical` | `("nome",)` | (same) | top-14 |
| `sp_severidade_alta_ranking` | `high` | `("inst",)` | `cat, causa, reinc, valor, spark[], cidade` | top-10 reinc ≥ 2 |
| `sp_severidade_critica_ranking` | `critical` | `("inst",)` | (same) | top-10 reinc ≥ 2 |
<!-- /AUTO-GENERATED:SP-SEVERIDADE -->

#### Notes specific to the SP severidade family

- All views are filtered to `regiao == "SP"` by the `_filter_sp_severidade` helper before aggregation. CE rows are dropped silently.
- Sprint 25 changed the default to `min_confidence="high"` for this family. Rows with `causa_canonica_confidence="low"` remain available to other aggregations, but they do not inflate Alta/Crítica dashboards unless the handler is called explicitly with a lower threshold.
- `pct_procedentes` is derived from `flag_resolvido_com_refaturamento`. Until the SP ingestion populates this flag (open debt), the field returns `0`.
- `cidade` in the ranking falls back to `SP/SP` when `municipio` is not present in the silver layer.
- Sparkline values are integers (count of orders per month) for the last 9 monthly buckets, left-padded with zeros if the installation has shorter history.
- Severity classification is read from `taxonomy_metadata()` in `src/ml/models/erro_leitura_classifier.py`. Two severities are supported in this family: `high` (alias `alta`) and `critical` (alias `critica`).
- `causa_canonica_confidence` is propagated by `prepare_dashboard_frame` and can be `high`, `low` or `indefinido`. Unknown values are treated as non-high for conservative severity views.

### CE Totais / Reclamações

| view_id | group_keys | metrics | notes |
|---|---|---|---|
| `ce_total_assunto_causa` | `("assunto", "causa_canonica")` | `qtd_total, percentual` | top causes per assunto |
| `monthly_assunto_breakdown` | `("mes_ingresso", "assunto")` | `qtd_erros` | seasonal diagnosis |
| `monthly_causa_breakdown` | `("mes_ingresso", "causa_canonica")` | `qtd_erros` | seasonal diagnosis |
| `motivos_taxonomia` | `("Categoria",)` | `Peso` | exposes the taxonomy v2 |

### SP — perfil técnico

| view_id | group_keys | metrics | notes |
|---|---|---|---|
| `sp_tipos_medidor` | `("tipo_medidor_dominante",)` | `qtd_ordens, percentual` | meter type distribution |
| `sp_tipos_medidor_digitacao` | `("tipo_medidor_dominante",)` | `qtd_ordens, percentual` | meter type subset filtered to typing errors |
| `sp_causas_por_tipo_medidor` | `("tipo_medidor_dominante", "causa_canonica")` | `qtd_ordens, percentual_no_tipo` | top causes per meter type |
| `sp_faturas_altas` | (varies) | (varies) | high invoice profile |
| `sp_fatura_medidor` | (varies) | (varies) | invoice × meter join |
| `sp_digitacao_fatura_medidor` | (varies) | (varies) | typing-error subset |
| `sp_medidores_problema_reclamacao` | (varies) | (varies) | meter complaints profile |
| `sp_perfil_assunto_lider` | (varies) | (varies) | leading topic profile |
| `sp_causa_observacoes` | (varies) | (varies) | sample observations per cause |

### Top instalações

| view_id | group_keys | metrics | notes |
|---|---|---|---|
| `top_instalacoes` | `("instalacao",)` | `qtd_ordens, taxa_refaturamento` | global top reincident |
| `top_instalacoes_por_regional` | `("regiao", "instalacao")` | `qtd_ordens` | per-region top |
| `top_instalacoes_digitacao` | `("regiao", "instalacao")` | `qtd_ordens` | typing-error subset |

### Refaturamento

| view_id | group_keys | metrics | notes |
|---|---|---|---|
| `refaturamento_summary` | `("status",)` | `taxa_refaturamento` | summary KPI |
| `refaturamento_by_cause` | `("causa_canonica",)` | `qtd_erros, taxa_refaturamento` | per-cause refat ratio |
| `radar_causes_by_region` | `("regiao", "causa_canonica")` | `percentual` | radar comparison |

## Performance contract

| Metric | SLO |
|---|---|
| p50 latency cold cache | ≤ 600 ms |
| p95 latency warm cache | ≤ 250 ms |
| Cache hit ratio (10m) | ≥ 0.7 |
| Payload size compressed | ≤ 64 KB |

Latency and cache events are exported as Prometheus histograms. Dashboards live under `infra/config/grafana/dashboards/`. Alerts under `infra/config/prometheus/alerts/`.

Sprint 24 also exports `enel_severity_sp_total{severity=...}` from the overview views so Grafana can show the current Alta + Crítica volume without parsing JSON payloads.

## Adding a new view — checklist

1. Implement the handler in `src/viz/erro_leitura_dashboard_data.py` (or domain-specific module).
2. Register one or more `ViewSpec` entries in `src/data_plane/views.py::VIEW_REGISTRY`.
3. Add unit tests under `tests/unit/test_*_views.py` covering: empty frame, alternative kwargs, region filter, edge values.
4. If introducing a new metric or column, document it in this file under the relevant section.
5. (Optional) Update `infra/config/grafana/dashboards/` if the view deserves observability.
