"""Daily Silver transformation DAG."""

from __future__ import annotations

from datetime import datetime

try:  # pragma: no cover
    from airflow.decorators import dag, task, task_group
    from airflow.sensors.external_task import ExternalTaskSensor
except ImportError:  # pragma: no cover
    dag = task = task_group = ExternalTaskSensor = None

if dag is not None:  # pragma: no cover
    from src.common.spark_session import create_spark_session
    from src.transformation.silver import TRANSFORMER_REGISTRY

    CADASTRO_TRANSFORMERS = [name for name in TRANSFORMER_REGISTRY if name.startswith("cadastro_")]
    TRANSACTIONAL_TRANSFORMERS = ["notas_operacionais", "entregas_fatura", "pagamentos", "metas_operacionais"]

    @dag(
        dag_id="transformation_silver_daily",
        schedule="0 7 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["transformation", "silver"],
    )
    def transformation_silver():
        wait_ingestion = ExternalTaskSensor(
            task_id="wait_ingestion",
            external_dag_id="ingestion_daily",
            mode="reschedule",
        )

        @task_group(group_id="cadastros_silver")
        def transform_cadastros():
            tasks = []
            for source_name in CADASTRO_TRANSFORMERS:
                @task(task_id=f"transform_{source_name}")
                def transform_source(current_source: str = source_name) -> int:
                    transformer = TRANSFORMER_REGISTRY[current_source](create_spark_session(memory="2g"))
                    return transformer.execute().silver_rows
                tasks.append(transform_source())
            return tasks

        @task_group(group_id="transacionais_silver")
        def transform_transacionais():
            tasks = []
            for source_name in TRANSACTIONAL_TRANSFORMERS:
                @task(task_id=f"transform_{source_name}")
                def transform_source(current_source: str = source_name) -> int:
                    transformer = TRANSFORMER_REGISTRY[current_source](create_spark_session(memory="2g"))
                    return transformer.execute().silver_rows
                tasks.append(transform_source())
            return tasks

        wait_ingestion >> transform_cadastros() >> transform_transacionais()

    transformation_silver()
