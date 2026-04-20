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

<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (90-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk vitest run          # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%)
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->