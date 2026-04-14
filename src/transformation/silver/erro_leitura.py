"""Silver transformer for erro de leitura complaints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.transformation.base import BaseSilverTransformer

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
else:  # pragma: no cover
    DataFrame = Any
    SparkSession = Any


class ErroLeituraSilverTransformer(BaseSilverTransformer):
    def __init__(self, spark: SparkSession) -> None:
        super().__init__("erro_leitura_normalizado", spark)

    def _bronze_table_name(self) -> str:
        return "nessie.bronze.descricoes_reclamacoes"

    def _silver_table_name(self) -> str:
        return "nessie.silver.erro_leitura_normalizado"

    def transform(self, df: DataFrame) -> DataFrame:
        from pyspark.sql.functions import col, concat_ws, current_timestamp, lower, regexp_replace, trim, upper

        cleaned = df
        for column in ["ordem", "instalacao", "grupo", "assunto", "status", "causa_raiz"]:
            if column in cleaned.columns:
                cleaned = cleaned.withColumn(column, upper(trim(col(column).cast("string"))))
        for column in ["observacao_ordem", "devolutiva"]:
            if column in cleaned.columns:
                cleaned = cleaned.withColumn(f"{column}_raw", col(column).cast("string"))
                cleaned = cleaned.withColumn(
                    column,
                    trim(lower(regexp_replace(regexp_replace(col(column).cast("string"), "<[^>]+>", " "), "\\s+", " "))),
                )
        cleaned = cleaned.withColumn("texto_completo", trim(concat_ws(" ", col("observacao_ordem"), col("devolutiva"))))
        cleaned = cleaned.withColumn("has_causa_raiz_label", col("causa_raiz").isNotNull())
        cleaned = cleaned.withColumn("_processed_at", current_timestamp())
        return self.add_silver_metadata(cleaned)

    def get_dedup_keys(self) -> list[str]:
        return ["ordem", "_source_region"]

    def get_dedup_order(self) -> str:
        return "_processed_at"
