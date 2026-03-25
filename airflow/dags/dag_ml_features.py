"""Daily feature materialization DAG."""

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
        dag_id="ml_features_daily",
        schedule="0 10 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["ml", "features"],
    )
    def ml_features_daily():
        wait_gold = ExternalTaskSensor(
            task_id="wait_gold",
            external_dag_id="dbt_gold_daily",
            mode="reschedule",
        )

        @task()
        def materialize_features() -> str:
            subprocess.run(
                [
                    "python",
                    "-m",
                    "scripts.materialize_features",
                    "--observation-date",
                    "{{ ds }}",
                ],
                check=True,
            )
            return "features materialized"

        wait_gold >> materialize_features()

    ml_features_daily()
