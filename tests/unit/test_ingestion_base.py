from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.base import BaseIngestor
from src.ingestion.config_loader import load_source_config


@dataclass
class FakeWriter:
    actions: list[str]

    def using(self, _format: str) -> "FakeWriter":
        self.actions.append("using")
        return self

    def append(self) -> None:
        self.actions.append("append")

    def create(self) -> None:
        self.actions.append("create")


class FakeDataFrame:
    def __init__(self, columns: list[str], row_count: int = 5) -> None:
        self.columns = columns
        self._row_count = row_count
        self.write_actions: list[str] = []

    def count(self) -> int:
        return self._row_count

    def withColumn(self, _name: str, _value) -> "FakeDataFrame":
        return self

    def writeTo(self, _table_name: str) -> FakeWriter:
        return FakeWriter(self.write_actions)

    def selectExpr(self, _expression: str) -> "FakeCollectFrame":
        return FakeCollectFrame([{"watermark_value": "2026-01-01 10:00:00"}])


class FakeCollectFrame:
    def __init__(self, rows):
        self._rows = rows

    def collect(self):
        return self._rows


class FakeCatalog:
    def tableExists(self, _table_name: str) -> bool:
        return False


class FakeSpark:
    def __init__(self) -> None:
        self.catalog = FakeCatalog()
        self.created_frames = []

    def createDataFrame(self, records):
        self.created_frames.append(records)
        return FakeDataFrame(columns=list(records[0].keys()))


class DummyIngestor(BaseIngestor):
    def extract(self):
        return FakeDataFrame(
            columns=[
                "cod_nota",
                "cod_uc",
                "cod_instalacao",
                "cod_distribuidora",
                "cod_ut",
                "cod_co",
                "cod_base",
                "tipo_servico",
                "flag_impacto_faturamento",
                "area_classificada_risco",
                "historico_incidentes_12m",
                "tipo_instalacao",
                "horario_agendado",
                "flag_risco_manual",
                "data_criacao",
                "status",
                "data_alteracao",
            ]
        )

    def _add_technical_metadata(self, df):  # type: ignore[override]
        return df

    def _resolve_watermark_value(self, _df):  # type: ignore[override]
        return "2026-01-01 10:00:00"


def test_base_ingestor_execute_returns_success() -> None:
    spark = FakeSpark()
    ingestor = DummyIngestor(load_source_config("notas_operacionais"), spark)
    result = ingestor.execute()
    assert result.status == "SUCCESS"
    assert result.rows_ingested == 5
    assert spark.created_frames
