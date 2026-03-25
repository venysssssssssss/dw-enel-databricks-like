"""Silver transformation for pagamentos."""

from __future__ import annotations

from src.ingestion.config_loader import load_source_config
from src.transformation.base import BaseSilverTransformer


class PagamentosSilverTransformer(BaseSilverTransformer):
    def __init__(self, spark) -> None:
        super().__init__("pagamentos", spark)
        self.contract = load_source_config("pagamentos")

    def get_dedup_keys(self) -> list[str]:
        return ["cod_pagamento"]

    def get_dedup_order(self) -> str:
        return "data_processamento"

    def transform(self, df):  # type: ignore[override]
        from pyspark.sql.functions import col, current_date, datediff, greatest, lit, regexp_replace, to_date, to_timestamp, when

        typed = (
            df.withColumn("valor_fatura", regexp_replace(col("valor_fatura"), ",", ".").cast("decimal(12,2)"))
            .withColumn("valor_pago", regexp_replace(col("valor_pago"), ",", ".").cast("decimal(12,2)"))
            .withColumn("data_vencimento", to_date(col("data_vencimento"), "dd/MM/yyyy"))
            .withColumn("data_pagamento", to_date(col("data_pagamento"), "dd/MM/yyyy"))
            .withColumn("data_processamento", to_timestamp(col("data_processamento"), "dd/MM/yyyy HH:mm:ss"))
        )
        transformed = (
            typed.withColumn(
                "flag_inadimplente",
                col("data_pagamento").isNull() & (datediff(current_date(), col("data_vencimento")) > 30),
            )
            .withColumn(
                "dias_atraso_pagamento",
                when(
                    col("data_pagamento").isNotNull(),
                    greatest(datediff(col("data_pagamento"), col("data_vencimento")), lit(0)),
                ).otherwise(datediff(current_date(), col("data_vencimento"))),
            )
        )
        return self.add_silver_metadata(transformed)
