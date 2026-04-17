# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Open-source lakehouse analytics platform for ENEL (energy distributor), replacing Databricks with equivalent open-source tooling. Strategy document: `estrategia_plataforma_analitica_preditiva_enel.docx`.

**Hardware target**: Notebook 16GB RAM DDR4, Intel i7-1185G7 (4c/8t), Intel Iris Xe (no GPU for ML). All services must respect memory limits via Docker profiles.

## Architecture

**Medallion pattern (Bronze → Silver → Gold)** on a lakehouse foundation:

- **Bronze**: Raw ingestion, exact replica with technical metadata (`_run_id`, `_ingested_at`, `_source_hash`, `_partition_date`)
- **Silver**: Typed, normalized, deduplicated. ACF/ASF classification, delay calculations, Haversine distance
- **Gold**: Dimensional model (star schema) via dbt Core. 10 dimensions + 7 fact tables

## Tech Stack

| Role | Tool | Version |
|------|------|---------|
| Object Storage | MinIO | RELEASE.2024+ |
| Table Format | Apache Iceberg | 1.5.x |
| Processing | Apache Spark (local mode) | 3.5.x |
| SQL Analytics | Trino | 440+ |
| Transformations | dbt Core | 1.8+ |
| Orchestration | Apache Airflow (SequentialExecutor) | 2.9+ |
| BI | Apache Superset | 4.0+ |
| ML | MLflow + LightGBM + XGBoost + scikit-learn | - |
| Data Quality | Great Expectations | 1.0+ |
| Catalog | Nessie | 0.80+ |
| Export APIs | FastAPI (Pydantic v2, async, streaming) | 0.115+ |
| Observability | Prometheus + Grafana | - |
| Language | Python | 3.12+ |

## Project Structure

```
src/
  ingestion/       # Bronze layer: BaseIngestor, CSVIngestor, IncrementalIngestor
  transformation/  # Silver layer: BaseSilverTransformer, processors/
  api/             # FastAPI: routers/, schemas/, services/, auth/
  ml/              # ML: features/, models/, scoring/, monitoring/
  quality/         # Great Expectations: expectations, checkpoints
  common/          # Shared: spark_session, minio_client, logging, config
dbt/               # dbt project: models/dimensions, models/marts
airflow/dags/      # 7 DAGs covering full lifecycle
infra/             # Docker Compose, Dockerfiles, service configs
tests/             # unit/ and integration/
docs/              # Technical docs: architecture, business-rules, ml, api, sprints
scripts/           # Setup, seed, sample data generation, smoke tests
```

## Common Commands

```bash
make setup              # Create venv and install dependencies
make dev                # Start dev profile (MinIO, Spark, Trino, Airflow, Nessie, PostgreSQL)
make full               # Start all services including Superset, Grafana, Prometheus
make down               # Stop all services
make test               # Run all tests
make test-unit          # Run unit tests only
make lint               # Run ruff + mypy
make pipeline           # Trigger full pipeline: ingest → transform → quality → dbt → ml
make smoke              # Run end-to-end smoke test
make trino-cli          # Open Trino CLI connected to Gold layer
```

## Business Domain

**Client**: ENEL energy distributor (Brazil). Data/rules in Portuguese.

**Key concepts**: ACF/ASF (risk classification), UT (technical unit), CO (operations center), Base/Polo, UC (consumption unit), Lote (batch). Detailed in `docs/business-rules/`.

**ML Models**:
- Delay prediction: LightGBM (binary + regression)
- Non-payment: XGBoost with calibrated probabilities
- Target projection: LightGBM + Logistic Regression ensemble
- Anomalies: Isolation Forest + Z-Score (unsupervised)

All CPU-only, tree-based. TimeSeriesSplit for validation (never random split).

## Key Principles

- Business rules live in pipelines and dimensional models, never in dashboards
- Every load has `run_id`, metadata, quality tests, and layer reconciliation
- Open-source only — no vendor lock-in
- BI first, ML only when underlying data is stable
- Point-in-time correct feature engineering (no data leakage)
- Spark in local mode with `shuffle.partitions=8` and `driver.memory=4g`

## Documentation Index

- Architecture: `docs/architecture/` (overview, tech stack, hardware sizing, data flow)
- Business Rules: `docs/business-rules/` (glossary, ACF/ASF rules, metrics, data sources)
- ML: `docs/ml/` (model selection, feature engineering, MLOps strategy)
- API: `docs/api/` (FastAPI design, endpoints, schemas)
- Sprints: `docs/sprints/` (12 sprints covering full implementation)

## RAG Environment (Sprint 17)

- `RAG_REGIONAL_SCOPE` default `CE+SP` (escopo regional do corpus de cards).
- `RAG_EMBEDDING_MODEL` default `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- `RAG_PROMPT_VERSION` default `2.0.0` (rollback: `1.0.0`).
- `RAG_LLM_JUDGE` default `0` (habilita avaliação de faithfulness opcional quando `1`).

<!-- dgc-policy-v11 -->
# Dual-Graph Context Policy

This project uses a local dual-graph MCP server for efficient context retrieval.

## MANDATORY: Always follow this order

1. **Call `graph_continue` first** — before any file exploration, grep, or code reading.

2. **If `graph_continue` returns `needs_project=true`**: call `graph_scan` with the
   current project directory (`pwd`). Do NOT ask the user.

3. **If `graph_continue` returns `skip=true`**: project has fewer than 5 files.
   Do NOT do broad or recursive exploration. Read only specific files if their names
   are mentioned, or ask the user what to work on.

4. **Read `recommended_files`** using `graph_read` — **one call per file**.
   - `graph_read` accepts a single `file` parameter (string). Call it separately for each
     recommended file. Do NOT pass an array or batch multiple files into one call.
   - `recommended_files` may contain `file::symbol` entries (e.g. `src/auth.ts::handleLogin`).
     Pass them verbatim to `graph_read(file: "src/auth.ts::handleLogin")` — it reads only
     that symbol's lines, not the full file.
   - Example: if `recommended_files` is `["src/auth.ts::handleLogin", "src/db.ts"]`,
     call `graph_read(file: "src/auth.ts::handleLogin")` and `graph_read(file: "src/db.ts")`
     as two separate calls (they can be parallel).

5. **Check `confidence` and obey the caps strictly:**
   - `confidence=high` -> Stop. Do NOT grep or explore further.
   - `confidence=medium` -> If recommended files are insufficient, call `fallback_rg`
     at most `max_supplementary_greps` time(s) with specific terms, then `graph_read`
     at most `max_supplementary_files` additional file(s). Then stop.
   - `confidence=low` -> Call `fallback_rg` at most `max_supplementary_greps` time(s),
     then `graph_read` at most `max_supplementary_files` file(s). Then stop.

## Token Usage

A `token-counter` MCP is available for tracking live token usage.

- To check how many tokens a large file or text will cost **before** reading it:
  `count_tokens({text: "<content>"})`
- To log actual usage after a task completes (if the user asks):
  `log_usage({input_tokens: <est>, output_tokens: <est>, description: "<task>"})`
- To show the user their running session cost:
  `get_session_stats()`

Live dashboard URL is printed at startup next to "Token usage".

## Rules

- Do NOT use `rg`, `grep`, or bash file exploration before calling `graph_continue`.
- Do NOT do broad/recursive exploration at any confidence level.
- `max_supplementary_greps` and `max_supplementary_files` are hard caps - never exceed them.
- Do NOT dump full chat history.
- Do NOT call `graph_retrieve` more than once per turn.
- After edits, call `graph_register_edit` with the changed files. Use `file::symbol` notation (e.g. `src/auth.ts::handleLogin`) when the edit targets a specific function, class, or hook.

## Context Store

Whenever you make a decision, identify a task, note a next step, fact, or blocker during a conversation, call `graph_add_memory`.

**To add an entry:**
```
graph_add_memory(type="decision|task|next|fact|blocker", content="one sentence max 15 words", tags=["topic"], files=["relevant/file.ts"])
```

**Do NOT write context-store.json directly** — always use `graph_add_memory`. It applies pruning and keeps the store healthy.

**Rules:**
- Only log things worth remembering across sessions (not every minor detail)
- `content` must be under 15 words
- `files` lists the files this decision/task relates to (can be empty)
- Log immediately when the item arises — not at session end

## Session End

When the user signals they are done (e.g. "bye", "done", "wrap up", "end session"), proactively update `CONTEXT.md` in the project root with:
- **Current Task**: one sentence on what was being worked on
- **Key Decisions**: bullet list, max 3 items
- **Next Steps**: bullet list, max 3 items

Keep `CONTEXT.md` under 20 lines total. Do NOT summarize the full conversation — only what's needed to resume next session.
