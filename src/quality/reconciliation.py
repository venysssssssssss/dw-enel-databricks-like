"""Automated reconciliation between lakehouse layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    run_id: str
    layer_pair: str
    table_name: str
    source_count: int
    target_count: int
    delta_count: int
    delta_pct: float
    status: str
    threshold_pct: float
    details: dict[str, object] | None = None


class LayerReconciler:
    def __init__(self, spark, thresholds: dict[str, float] | None = None) -> None:
        self.spark = spark
        self.thresholds = thresholds or {
            "bronze_to_silver": 0.05,
            "silver_to_gold": 0.10,
        }

    def reconcile(
        self,
        source_table: str,
        target_table: str,
        layer_pair: str,
        join_keys: list[str] | None = None,
    ) -> ReconciliationResult:
        source_count = int(self.spark.table(source_table).count())
        target_count = int(self.spark.table(target_table).count())
        delta_count = source_count - target_count
        delta_pct = abs(delta_count) / max(source_count, 1)
        threshold = self.thresholds[layer_pair]
        status = "OK" if delta_pct <= threshold else ("WARNING" if delta_pct <= threshold * 2 else "FAIL")
        result = ReconciliationResult(
            run_id=str(uuid4()),
            layer_pair=layer_pair,
            table_name=target_table.split(".")[-1],
            source_count=source_count,
            target_count=target_count,
            delta_count=delta_count,
            delta_pct=round(delta_pct * 100, 2),
            status=status,
            threshold_pct=threshold * 100,
            details={"join_keys": join_keys or []},
        )
        self._persist_result(result)
        return result

    def _persist_result(self, result: ReconciliationResult) -> None:
        try:
            audit_table = "nessie.audit.reconciliation_log"
            audit_df = self.spark.createDataFrame(
                [
                    {
                        "run_id": result.run_id,
                        "layer_pair": result.layer_pair,
                        "table_name": result.table_name,
                        "source_count": result.source_count,
                        "target_count": result.target_count,
                        "delta_count": result.delta_count,
                        "delta_pct": result.delta_pct,
                        "status": result.status,
                        "threshold_pct": result.threshold_pct,
                        "executed_at": datetime.now(),
                    }
                ]
            )
            writer = audit_df.writeTo(audit_table).using("iceberg")
            if self.spark.catalog.tableExists(audit_table):
                writer.append()
            else:
                writer.create()
        except Exception as exc:  # pragma: no cover
            logger.warning("reconciliation_persist_failed", error=str(exc), table=result.table_name)
