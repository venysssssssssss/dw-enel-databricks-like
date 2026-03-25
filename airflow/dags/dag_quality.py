"""Daily quality DAG for checkpoints and reconciliation."""

from __future__ import annotations

from datetime import datetime

try:  # pragma: no cover
    from airflow.decorators import dag, task
except ImportError:  # pragma: no cover
    dag = task = None

if dag is not None:  # pragma: no cover
    from src.common.spark_session import create_spark_session
    from src.quality.alerts import QualityAlertManager
    from src.quality.gx_runner import GreatExpectationsRunner
    from src.quality.reconciliation import LayerReconciler
    from src.quality.suites import build_default_checkpoints

    @dag(dag_id="data_quality_daily", schedule="0 8 * * *", start_date=datetime(2026, 1, 1), catchup=False, tags=["quality"])
    def data_quality():
        @task()
        def run_bronze_checks() -> dict[str, int]:
            runner = GreatExpectationsRunner()
            checkpoint = [item for item in build_default_checkpoints() if item.name == "checkpoint_bronze_daily"][0]
            return runner.run_checkpoint(checkpoint)

        @task()
        def run_silver_checks() -> dict[str, int]:
            runner = GreatExpectationsRunner()
            checkpoint = [item for item in build_default_checkpoints() if item.name == "checkpoint_silver_daily"][0]
            return runner.run_checkpoint(checkpoint)

        @task()
        def run_reconciliation() -> list[dict[str, object]]:
            spark = create_spark_session(memory="2g")
            reconciler = LayerReconciler(spark)
            results = []
            for table_name in ["notas_operacionais", "entregas_fatura", "pagamentos"]:
                result = reconciler.reconcile(
                    f"nessie.bronze.{table_name}",
                    f"nessie.silver.{table_name}",
                    "bronze_to_silver",
                )
                results.append(result.__dict__)
            return results

        @task()
        def generate_quality_report(bronze_stats: dict[str, int], silver_stats: dict[str, int], recon_results: list[dict[str, object]]) -> int:
            QualityAlertManager().evaluate_and_alert(
                {"success": True, "table_name": "checkpoint", "expectation": "summary"},
                [],
            )
            return len(recon_results) + bronze_stats["validation_count"] + silver_stats["validation_count"]

        bronze_stats = run_bronze_checks()
        silver_stats = run_silver_checks()
        reconciliation = run_reconciliation()
        generate_quality_report(bronze_stats, silver_stats, reconciliation)

    data_quality()
