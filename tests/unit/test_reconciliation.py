from __future__ import annotations

from src.quality.reconciliation import LayerReconciler


class FakeTable:
    def __init__(self, count_value: int) -> None:
        self._count_value = count_value

    def count(self) -> int:
        return self._count_value


class FakeAuditWriter:
    def using(self, _format: str):
        return self

    def append(self) -> None:
        return None

    def create(self) -> None:
        return None


class FakeAuditFrame:
    def writeTo(self, _table: str) -> FakeAuditWriter:
        return FakeAuditWriter()


class FakeCatalog:
    def tableExists(self, _table_name: str) -> bool:
        return False


class FakeSpark:
    def __init__(self) -> None:
        self.catalog = FakeCatalog()

    def table(self, table_name: str) -> FakeTable:
        return FakeTable(100 if "bronze" in table_name else 96)

    def createDataFrame(self, _rows) -> FakeAuditFrame:
        return FakeAuditFrame()


def test_reconciliation_ok_when_delta_within_threshold() -> None:
    result = LayerReconciler(FakeSpark()).reconcile(
        "nessie.bronze.notas_operacionais",
        "nessie.silver.notas_operacionais",
        "bronze_to_silver",
    )
    assert result.status == "OK"
    assert result.delta_count == 4
