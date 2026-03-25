.PHONY: setup setup-all dev full ml down test test-unit test-integration lint format pipeline smoke sample-data seed-time features train score drift

setup:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/pre-commit install

setup-all:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -e ".[dev,api,ml,platform]"
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
