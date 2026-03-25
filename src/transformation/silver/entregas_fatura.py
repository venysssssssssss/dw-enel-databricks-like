"""Silver transformation for entrega de faturas."""

from __future__ import annotations

from src.ingestion.config_loader import load_source_config
from src.transformation.base import BaseSilverTransformer


class EntregasFaturaSilverTransformer(BaseSilverTransformer):
    def __init__(self, spark) -> None:
        super().__init__("entregas_fatura", spark)
        self.contract = load_source_config("entregas_fatura")

    def get_dedup_keys(self) -> list[str]:
        return ["cod_entrega"]

    def get_dedup_order(self) -> str:
        return "data_registro"

    def transform(self, df):  # type: ignore[override]
        from pyspark.sql.functions import col, datediff, lit, udf, when
        from pyspark.sql.types import DoubleType

        from src.transformation.processors.business_rules import haversine_meters
        from src.transformation.processors.type_caster import apply_schema_types

        haversine_udf = udf(haversine_meters, DoubleType())
        typed = apply_schema_types(df, self.contract.columns)
        transformed = (
            typed.withColumn(
                "distancia_metros",
                haversine_udf(
                    col("lat_entrega"),
                    col("lon_entrega"),
                    col("lat_uc"),
                    col("lon_uc"),
                ),
            )
            .withColumn("flag_dentro_coordenada", col("distancia_metros") <= lit(100.0))
            .withColumn(
                "flag_antes_vencimento",
                when(col("data_entrega").isNull(), lit(False)).otherwise(
                    datediff(col("data_vencimento"), col("data_entrega")) >= 5
                ),
            )
            .withColumn(
                "dias_para_entrega",
                when(col("data_entrega").isNull(), lit(None)).otherwise(
                    datediff(col("data_entrega"), col("data_emissao"))
                ),
            )
        )
        return self.add_silver_metadata(transformed)
