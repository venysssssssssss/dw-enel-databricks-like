"""Daily scoring DAG."""

from __future__ import annotations

from datetime import datetime

try:  # pragma: no cover
    from airflow.decorators import dag, task
    from airflow.sensors.external_task import ExternalTaskSensor
except ImportError:  # pragma: no cover
    dag = task = ExternalTaskSensor = None

if dag is not None:  # pragma: no cover
    import subprocess

    @dag(
        dag_id="ml_scoring_daily",
        schedule="0 11 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["ml", "scoring"],
    )
    def ml_scoring_daily():
        wait_features = ExternalTaskSensor(
            task_id="wait_features",
            external_dag_id="ml_features_daily",
            mode="reschedule",
        )

        @task()
        def score_models() -> str:
            subprocess.run(
                [
                    "python",
                    "-m",
                    "scripts.score_models",
                    "--scoring-date",
                    "{{ ds }}",
                ],
                check=True,
            )
            return "scores generated"

        wait_features >> score_models()

    ml_scoring_daily()
