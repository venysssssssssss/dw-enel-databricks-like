"""Silver transformation for notas operacionais."""

from __future__ import annotations

from src.ingestion.config_loader import load_source_config
from src.transformation.base import BaseSilverTransformer


class NotasOperacionaisSilverTransformer(BaseSilverTransformer):
    def __init__(self, spark) -> None:
        super().__init__("notas_operacionais", spark)
        self.contract = load_source_config("notas_operacionais")

    def get_dedup_keys(self) -> list[str]:
        return ["cod_nota"]

    def get_dedup_order(self) -> str:
        return "data_alteracao"

    def transform(self, df):  # type: ignore[override]
        from pyspark.sql.functions import col, current_date, datediff, lit, trim, upper, when

        from src.transformation.processors.type_caster import apply_schema_types

        df = apply_schema_types(df, self.contract.columns)
        df = (
            df.withColumn("tipo_servico", upper(trim(col("tipo_servico"))))
            .withColumn("status", upper(trim(col("status"))))
            .withColumn(
                "classificacao_acf_asf",
                when(
                    col("flag_impacto_faturamento")
                    & col("tipo_servico").isin(
                        "CORTE",
                        "RELIGACAO",
                        "SUBSTITUICAO_MEDIDOR",
                        "INSTALACAO_MEDIDOR",
                        "REGULARIZACAO_FRAUDE",
                    ),
                    lit("ACF_A"),
                )
                .when(
                    col("flag_impacto_faturamento")
                    & col("tipo_servico").isin(
                        "INSPECAO_PROGRAMADA",
                        "VERIFICACAO_MEDIDOR",
                        "ATUALIZACAO_CADASTRAL_COM_MEDICAO",
                        "REVISAO_LEITURA",
                    ),
                    lit("ACF_B"),
                )
                .when(col("flag_impacto_faturamento"), lit("ACF_C"))
                .when(
                    col("area_classificada_risco")
                    | (col("historico_incidentes_12m") >= 2)
                    | col("tipo_instalacao").isin(
                        "SUBESTACAO",
                        "ALTA_TENSAO",
                        "AREA_INDUSTRIAL_RISCO",
                        "ZONA_RURAL_ISOLADA",
                    )
                    | (~col("horario_agendado").between("06:00", "18:00"))
                    | col("flag_risco_manual"),
                    lit("ASF_RISCO"),
                )
                .otherwise(lit("ASF_FORA_RISCO")),
            )
            .withColumn(
                "dias_atraso",
                when(
                    col("data_execucao").isNotNull() & (col("data_execucao") > col("data_prevista")),
                    datediff(col("data_execucao"), col("data_prevista")),
                )
                .when(
                    col("data_execucao").isNull() & (current_date() > col("data_prevista")),
                    datediff(current_date(), col("data_prevista")),
                )
                .otherwise(lit(0)),
            )
            .withColumn(
                "status_atraso",
                when(
                    col("data_execucao").isNotNull() & (col("data_execucao") <= col("data_prevista")),
                    lit("NO_PRAZO"),
                )
                .when(
                    col("data_execucao").isNotNull() & (col("data_execucao") > col("data_prevista")),
                    lit("ATRASADO"),
                )
                .when(
                    col("data_execucao").isNull() & (current_date() <= col("data_prevista")),
                    lit("PENDENTE_NO_PRAZO"),
                )
                .otherwise(lit("PENDENTE_FORA_PRAZO"))
            )
            .withColumn("flag_risco", col("classificacao_acf_asf") == lit("ASF_RISCO"))
        )
        return self.add_silver_metadata(df)
