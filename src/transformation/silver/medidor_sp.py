"""Silver transformation for SP meter profile."""

from __future__ import annotations

from src.ingestion.config_loader import load_source_config
from src.transformation.base import BaseSilverTransformer


class MedidorSpSilverTransformer(BaseSilverTransformer):
    def __init__(self, spark) -> None:
        super().__init__("medidor_sp", spark)
        self.contract = load_source_config("medidor_sp")

    def get_dedup_keys(self) -> list[str]:
        return ["instalacao"]

    def get_dedup_order(self) -> str:
        return "_processed_at"

    def transform(self, df):  # type: ignore[override]
        from pyspark.sql import Window
        from pyspark.sql.functions import (
            col,
            count,
            countDistinct,
            regexp_replace,
            row_number,
            trim,
            upper,
            when,
        )
        from pyspark.sql.types import BooleanType, IntegerType

        normalized = (
            df.withColumn("instalacao", regexp_replace(trim(col("instalacao").cast("string")), r"\.0$", ""))
            .withColumn("equipamento", trim(col("equipamento").cast("string")))
            .withColumn("grp_reg", trim(col("grp_reg").cast("string")))
            .withColumn("tipo", trim(col("tipo").cast("string")))
            .withColumn("tipo", when(col("tipo") == "", None).otherwise(upper(col("tipo"))))
        )

        type_count = normalized.groupBy("instalacao", "tipo").agg(count("*").alias("qtd_tipo"))
        ranking_window = Window.partitionBy("instalacao").orderBy(col("qtd_tipo").desc(), col("tipo").asc())
        dominant = (
            type_count.withColumn("_rn", row_number().over(ranking_window))
            .filter(col("_rn") == 1)
            .drop("_rn")
            .withColumnRenamed("tipo", "tipo_medidor_dominante")
        )
        stats = (
            normalized.groupBy("instalacao")
            .agg(
                countDistinct("equipamento").cast(IntegerType()).alias("equipamentos_unicos"),
                countDistinct("tipo").cast(IntegerType()).alias("tipos_distintos"),
            )
            .withColumn(
                "instalacao_multi_tipo",
                (col("tipos_distintos") > 1).cast(BooleanType()),
            )
        )
        transformed = dominant.join(stats, on="instalacao", how="left")
        return self.add_silver_metadata(transformed)
