from __future__ import annotations

from src.quality.alerts import QualityAlertManager
from src.quality.reconciliation import ReconciliationResult


def test_alert_manager_creates_alert_for_failed_reconciliation() -> None:
    manager = QualityAlertManager()
    alerts = manager.evaluate_and_alert(
        {"success": True},
        [
            ReconciliationResult(
                run_id="1",
                layer_pair="bronze_to_silver",
                table_name="notas_operacionais",
                source_count=100,
                target_count=70,
                delta_count=30,
                delta_pct=30.0,
                status="FAIL",
                threshold_pct=5.0,
            )
        ],
    )
    assert len(alerts) == 1
    assert alerts[0].severity == "HIGH"
