"""Daily dbt Gold DAG."""

from __future__ import annotations

from datetime import datetime

try:  # pragma: no cover
    from airflow.decorators import dag, task
    from airflow.sensors.external_task import ExternalTaskSensor
except ImportError:  # pragma: no cover
    dag = task = ExternalTaskSensor = None

if dag is not None:  # pragma: no cover
    import subprocess

    DBT_PROJECT_DIR = "/opt/airflow/dbt"

    @dag(
        dag_id="dbt_gold_daily",
        schedule="0 9 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["dbt", "gold"],
    )
    def dbt_gold():
        wait_quality = ExternalTaskSensor(
            task_id="wait_quality",
            external_dag_id="data_quality_daily",
            mode="reschedule",
        )

        @task()
        def dbt_seed() -> str:
            subprocess.run(["dbt", "seed", "--project-dir", DBT_PROJECT_DIR], check=True)
            return "dbt seed ok"

        @task()
        def dbt_run_dimensions() -> str:
            subprocess.run(
                ["dbt", "run", "--select", "dimensions", "--project-dir", DBT_PROJECT_DIR],
                check=True,
            )
            return "dbt dimensions ok"

        @task()
        def dbt_run_marts() -> str:
            subprocess.run(
                ["dbt", "run", "--select", "marts", "--project-dir", DBT_PROJECT_DIR],
                check=True,
            )
            return "dbt marts ok"

        @task()
        def dbt_test() -> str:
            subprocess.run(["dbt", "test", "--project-dir", DBT_PROJECT_DIR], check=True)
            return "dbt tests ok"

        wait_quality >> dbt_seed() >> dbt_run_dimensions() >> dbt_run_marts() >> dbt_test()

    dbt_gold()
