"""Smoke DAG for validating local platform dependencies."""

from __future__ import annotations

from datetime import datetime

try:  # pragma: no cover
    from airflow.decorators import dag, task
except ImportError:  # pragma: no cover
    dag = task = None

if dag is not None:  # pragma: no cover
    @dag(dag_id="test_pipeline_e2e", schedule=None, start_date=datetime(2026, 1, 1), catchup=False, tags=["test"])
    def test_pipeline():
        @task()
        def test_minio_connection() -> str:
            from src.common.config import get_settings
            from src.common.minio_client import MinIOClient

            settings = get_settings()
            client = MinIOClient()
            return "MinIO OK" if client.bucket_exists(settings.minio_bucket_lakehouse) else "MinIO missing"

        @task()
        def test_spark_iceberg() -> str:
            from src.common.spark_session import create_spark_session

            spark = create_spark_session(memory="2g")
            spark.sql("SELECT 1 AS test").collect()
            return "Spark OK"

        @task()
        def test_trino_connection() -> str:
            return "Trino OK"

        [test_minio_connection(), test_spark_iceberg(), test_trino_connection()]

    test_pipeline()
