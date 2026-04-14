"""Erro de leitura intelligence DAG."""

from __future__ import annotations

from datetime import datetime

try:  # pragma: no cover
    from airflow.decorators import dag, task
except ImportError:  # pragma: no cover
    dag = task = None

if dag is not None:  # pragma: no cover
    import subprocess

    @dag(
        dag_id="erro_leitura_intelligence_daily",
        schedule="30 10 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["erro-leitura", "ia", "ml"],
    )
    def erro_leitura_intelligence_daily():
        @task()
        def ingest_descricoes() -> str:
            subprocess.run(
                ["python", "-m", "src.ingestion.descricoes_enel_ingestor", "--input-dir", "DESCRICOES_ENEL"],
                check=True,
            )
            return "bronze ok"

        @task()
        def silver_normalize() -> str:
            subprocess.run(["python", "-m", "scripts.normalize_erro_leitura"], check=True)
            return "silver ok"

        @task()
        def dbt_gold() -> str:
            subprocess.run(
                ["dbt", "run", "--select", "marts/erro_leitura", "--project-dir", "/opt/airflow/dbt"],
                check=True,
            )
            return "gold ok"

        @task()
        def train_text_models() -> str:
            subprocess.run(["python", "-m", "scripts.train_erro_leitura"], check=True)
            return "ml ok"

        ingest_descricoes() >> silver_normalize() >> dbt_gold() >> train_text_models()

    erro_leitura_intelligence_daily()
