"""Quality alerting primitives for failed validations and reconciliation drift."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from src.common.logging import get_logger
from src.common.serialization import to_json
from src.quality.reconciliation import ReconciliationResult

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class QualityAlert:
    severity: str
    table_name: str
    expectation: str
    details: dict[str, object]
    created_at: datetime


class QualityAlertManager:
    def __init__(self, spark: object | None = None) -> None:
        self.spark = spark

    def evaluate_and_alert(
        self,
        ge_result: dict[str, object] | None,
        recon_results: list[ReconciliationResult],
    ) -> list[QualityAlert]:
        alerts: list[QualityAlert] = []
        if ge_result and not bool(ge_result.get("success", True)):
            alerts.append(
                QualityAlert(
                    severity="HIGH",
                    table_name=str(ge_result.get("table_name", "unknown")),
                    expectation=str(ge_result.get("expectation", "checkpoint")),
                    details={key: value for key, value in ge_result.items() if key not in {"table_name", "expectation"}},
                    created_at=datetime.now(),
                )
            )
        for reconciliation in recon_results:
            if reconciliation.status in {"WARNING", "FAIL"}:
                alerts.append(
                    QualityAlert(
                        severity="HIGH" if reconciliation.status == "FAIL" else "MEDIUM",
                        table_name=reconciliation.table_name,
                        expectation="reconciliation",
                        details={"delta_pct": reconciliation.delta_pct, "threshold_pct": reconciliation.threshold_pct},
                        created_at=datetime.now(),
                    )
                )
        for alert in alerts:
            logger.warning("quality_alert", **asdict(alert))
        self._persist_alerts(alerts)
        return alerts

    def _persist_alerts(self, alerts: list[QualityAlert]) -> None:
        if self.spark is None or not alerts:
            return
        try:
            audit_table = "nessie.audit.quality_alerts"
            alert_df = self.spark.createDataFrame(
                [{**asdict(alert), "details": to_json(alert.details)} for alert in alerts]
            )
            writer = alert_df.writeTo(audit_table).using("iceberg")
            if self.spark.catalog.tableExists(audit_table):
                writer.append()
            else:
                writer.create()
        except Exception as exc:  # pragma: no cover
            logger.warning("quality_alert_persist_failed", error=str(exc))
