"""Daily Bronze ingestion DAG."""

from __future__ import annotations

from datetime import datetime, timedelta

try:  # pragma: no cover
    from airflow.decorators import dag, task, task_group
except ImportError:  # pragma: no cover
    dag = task = task_group = None

if dag is not None:  # pragma: no cover
    from src.common.spark_session import create_spark_session
    from src.ingestion.config_loader import load_source_config
    from src.ingestion.sources import INGESTION_SOURCE_REGISTRY

    DEFAULT_ARGS = {
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
    }
    CADASTRO_SOURCES = [name for name in INGESTION_SOURCE_REGISTRY if name.startswith("cadastro_")]
    OPERATIONAL_SOURCES = ["notas_operacionais", "entregas_fatura", "pagamentos", "metas_operacionais"]

    @dag(
        dag_id="ingestion_daily",
        schedule="0 6 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        default_args=DEFAULT_ARGS,
        max_active_runs=1,
        tags=["ingestion", "bronze"],
    )
    def ingestion_daily():
        @task_group(group_id="cadastros")
        def ingest_cadastros():
            tasks = []
            for source_name in CADASTRO_SOURCES:
                @task(task_id=f"ingest_{source_name}")
                def ingest_source(current_source: str = source_name) -> int:
                    config = load_source_config(current_source)
                    ingestor = INGESTION_SOURCE_REGISTRY[current_source](config, create_spark_session(memory="2g"))
                    return ingestor.execute().rows_ingested
                tasks.append(ingest_source())
            return tasks

        @task_group(group_id="operacionais")
        def ingest_operacionais():
            tasks = []
            for source_name in OPERATIONAL_SOURCES:
                @task(task_id=f"ingest_{source_name}")
                def ingest_source(current_source: str = source_name) -> int:
                    config = load_source_config(current_source)
                    ingestor = INGESTION_SOURCE_REGISTRY[current_source](config, create_spark_session(memory="2g"))
                    return ingestor.execute().rows_ingested
                tasks.append(ingest_source())
            return tasks

        @task()
        def log_summary() -> str:
            return "Resumo de ingestão registrado."

        ingest_cadastros()
        ingest_operacionais()
        log_summary()

    ingestion_daily()
