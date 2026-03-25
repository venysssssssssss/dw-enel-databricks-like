"""Daily drift-monitoring DAG."""

from __future__ import annotations

from datetime import datetime, timedelta

try:  # pragma: no cover
    from airflow.decorators import dag, task
    from airflow.sensors.external_task import ExternalTaskSensor
except ImportError:  # pragma: no cover
    dag = task = ExternalTaskSensor = None

if dag is not None:  # pragma: no cover
    import subprocess

    MODELS = ["atraso_entrega", "inadimplencia", "metas", "anomalias"]

    @dag(
        dag_id="ml_monitoring_daily",
        schedule="0 12 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["ml", "monitoring"],
    )
    def ml_monitoring_daily():
        wait_scoring = ExternalTaskSensor(
            task_id="wait_scoring",
            external_dag_id="ml_scoring_daily",
            mode="reschedule",
        )

        @task()
        def run_drift(model_name: str) -> str:
            reference_date = "{{ macros.ds_add(ds, -7) }}"
            subprocess.run(
                [
                    "python",
                    "-m",
                    "scripts.check_drift",
                    "--model-name",
                    model_name,
                    "--reference-date",
                    reference_date,
                    "--current-date",
                    "{{ ds }}",
                ],
                check=True,
            )
            return model_name

        wait_scoring >> [run_drift(model_name) for model_name in MODELS]

    ml_monitoring_daily()
