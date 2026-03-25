"""Silver transformation for metas operacionais."""

from __future__ import annotations

from src.transformation.base import BaseSilverTransformer


class MetasOperacionaisSilverTransformer(BaseSilverTransformer):
    def __init__(self, spark) -> None:
        super().__init__("metas_operacionais", spark)

    def get_dedup_keys(self) -> list[str]:
        return ["mes_referencia", "cod_base", "indicador"]

    def get_dedup_order(self) -> str:
        return "_ingested_at"

    def transform(self, df):  # type: ignore[override]
        from pyspark.sql.functions import col, lit, upper, when

        transformed = (
            df.withColumn("indicador", upper(col("indicador")))
            .withColumn("valor_meta", col("valor_meta").cast("double"))
            .withColumn("valor_realizado", col("valor_realizado").cast("double"))
            .withColumn("pct_atingimento", (col("valor_realizado") / col("valor_meta")) * lit(100.0))
            .withColumn(
                "status_meta",
                when(col("pct_atingimento") >= 100, lit("ATINGIDA"))
                .when(col("pct_atingimento") >= 90, lit("EM_RISCO"))
                .when(col("pct_atingimento") >= 70, lit("CRITICA"))
                .otherwise(lit("NAO_ATINGIDA")),
            )
        )
        return self.add_silver_metadata(transformed)
