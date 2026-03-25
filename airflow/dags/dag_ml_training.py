"""Weekly ML training DAG."""

from __future__ import annotations

from datetime import datetime

try:  # pragma: no cover
    from airflow.decorators import dag, task
except ImportError:  # pragma: no cover
    dag = task = None

if dag is not None:  # pragma: no cover
    import subprocess

    @dag(
        dag_id="ml_training_weekly",
        schedule="0 5 * * 1",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["ml", "training"],
    )
    def ml_training_weekly():
        @task()
        def train_models() -> str:
            subprocess.run(
                [
                    "python",
                    "-m",
                    "scripts.train_models",
                    "--test-date",
                    "{{ ds }}",
                ],
                check=True,
            )
            return "models trained"

        train_models()

    ml_training_weekly()
