"""Silver transformation for SP invoice complaints."""

from __future__ import annotations

from src.ingestion.config_loader import load_source_config
from src.transformation.base import BaseSilverTransformer


class FaturaReclamadaSpSilverTransformer(BaseSilverTransformer):
    def __init__(self, spark) -> None:
        super().__init__("fatura_reclamada_sp", spark)
        self.contract = load_source_config("fatura_reclamada_sp")

    def get_dedup_keys(self) -> list[str]:
        return ["id_reclamacao", "doc_impressao"]

    def get_dedup_order(self) -> str:
        return "_processed_at"

    def transform(self, df):  # type: ignore[override]
        from pyspark.sql.functions import (
            col,
            datediff,
            regexp_replace,
            to_timestamp,
            trim,
            when,
        )

        typed = (
            df.withColumn("id_reclamacao", regexp_replace(trim(col("id_reclamacao").cast("string")), r"\.0$", ""))
            .withColumn("doc_impressao", trim(col("doc_impressao").cast("string")))
            .withColumn("fat_reclamada", trim(col("fat_reclamada").cast("string")))
            .withColumn(
                "valor_fat_reclamada",
                regexp_replace(col("valor_fat_reclamada").cast("string"), ",", ".").cast("decimal(12,2)"),
            )
            .withColumn("data_emissao_fat", to_timestamp(col("data_emissao_fat")))
            .withColumn("data_vencimento", to_timestamp(col("data_vencimento")))
            .withColumn("data_reclamacao", to_timestamp(col("data_reclamacao")))
            .withColumn("ordem", col("id_reclamacao"))
        )
        transformed = (
            typed.withColumn(
                "dias_emissao_ate_reclamacao",
                when(
                    col("data_reclamacao").isNotNull() & col("data_emissao_fat").isNotNull(),
                    datediff(col("data_reclamacao"), col("data_emissao_fat")),
                ),
            )
            .withColumn(
                "dias_vencimento_ate_reclamacao",
                when(
                    col("data_reclamacao").isNotNull() & col("data_vencimento").isNotNull(),
                    datediff(col("data_reclamacao"), col("data_vencimento")),
                ),
            )
        )
        return self.add_silver_metadata(transformed)
