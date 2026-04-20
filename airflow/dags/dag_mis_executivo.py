"""DAG para ingestão e transformação das Reclamações CE (Sprint 21 - MIS Executivo)."""

import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "data_engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "mis_executivo_ce",
    default_args=default_args,
    description="Pipeline de ingestão e normalização das descrições do Ceará",
    schedule_interval="0 3 * * *",
    start_date=datetime(2026, 5, 25),
    catchup=False,
    tags=["mis", "ce", "bronze", "silver", "nlp"],
) as dag:

    run_pipeline_bronze_silver = BashOperator(
        task_id="run_ingestion_and_silver_transformation",
        bash_command="python scripts/run_ingestion.py --mis-ce",
        # Assumindo que criaremos um wrapper em scripts/ ou rodaremos o módulo direto
        # python -m src.ingestion.pipeline_mis_ce
    )

    run_pipeline_bronze_silver
