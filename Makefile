.PHONY: setup setup-all dev full ml down test test-unit test-integration lint format pipeline smoke sample-data seed-time features train score drift erro-leitura-dry-run erro-leitura-normalize erro-leitura-train erro-leitura-dashboard share-up share-url share-logs share-down rag-rebuild test-rag-evals test-rag

setup:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/pre-commit install

setup-all:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev,api,ml,platform,viz]"
	.venv/bin/pre-commit install

dev:
	docker compose -f infra/docker-compose.dev.yml up -d

full:
	docker compose -f infra/docker-compose.full.yml up -d

ml:
	docker compose -f infra/docker-compose.ml.yml up -d

down:
	docker compose -f infra/docker-compose.dev.yml down --remove-orphans

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	ruff check src/ tests/ scripts/
	mypy src/ scripts/

format:
	ruff format src/ tests/ scripts/

pipeline:
	python -m scripts.generate_sample_data

smoke:
	python -m scripts.seed_dim_tempo --output data/sample/dim_tempo.csv

sample-data:
	python -m scripts.generate_sample_data --rows 1000

seed-time:
	python -m scripts.seed_dim_tempo --output data/sample/dim_tempo.csv

features:
	python -m scripts.materialize_features --observation-date 2026-03-01

train:
	python -m scripts.train_models --test-date 2026-03-01

score:
	python -m scripts.score_models --scoring-date 2026-03-01

drift:
	python -m scripts.check_drift --model-name atraso_entrega --reference-date 2026-02-01 --current-date 2026-03-01

erro-leitura-dry-run:
	python -m src.ingestion.descricoes_enel_ingestor --input-dir DESCRICOES_ENEL --dry-run

erro-leitura-normalize:
	python -m scripts.normalize_erro_leitura --input-dir DESCRICOES_ENEL

erro-leitura-train:
	python -m scripts.train_erro_leitura --input data/silver/erro_leitura_normalizado.csv

erro-leitura-dashboard:
	.venv/bin/streamlit run apps/streamlit/erro_leitura_dashboard.py

# --- Compartilhamento publico do dashboard (Streamlit + Caddy + Cloudflare Tunnel) ---
# Ver docs/SHARE_DASHBOARD.md para detalhes.
share-up:
	./scripts/share_dashboard.sh up

share-url:
	./scripts/share_dashboard.sh url

share-logs:
	./scripts/share_dashboard.sh logs

share-down:
	./scripts/share_dashboard.sh down

rag-rebuild:
	poetry run python scripts/rebuild_rag_corpus_regional.py \
		--regional-scope $${REGIONAL_SCOPE:-CE+SP}

test-rag-evals:
	poetry run python scripts/rag_eval_regional.py \
		--golden tests/evals/rag_sp_ce_golden.jsonl \
		--gate-recall5 0.85 \
		--gate-regional-compliance 1.0 \
		--gate-refusal 0.95 \
		--gate-citation 0.80 \
		--gate-exactness 0.75

test-rag: test-rag-evals
	pytest tests/unit/rag/ tests/integration/test_rag_*.py -v
