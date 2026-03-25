"""Declarative suites for Bronze and Silver quality checks."""

from __future__ import annotations

from src.quality.contracts import CheckpointDefinition, ExpectationDefinition, ValidationSuite


def build_bronze_suites() -> tuple[ValidationSuite, ...]:
    return (
        ValidationSuite(
            name="bronze_notas_operacionais",
            table_name="nessie.bronze.notas_operacionais",
            expectations=(
                ExpectationDefinition("expect_table_row_count_to_be_greater_than", {"value": 100}, critical=True),
                ExpectationDefinition("expect_column_values_to_not_be_null", {"column": "_run_id"}, critical=True),
                ExpectationDefinition("expect_column_values_to_not_be_null", {"column": "_ingested_at"}, critical=True),
            ),
        ),
        ValidationSuite(
            name="bronze_entregas_fatura",
            table_name="nessie.bronze.entregas_fatura",
            expectations=(
                ExpectationDefinition("expect_table_row_count_to_be_greater_than", {"value": 100}, critical=True),
                ExpectationDefinition("expect_column_values_to_not_be_null", {"column": "cod_entrega"}, critical=True),
            ),
        ),
        ValidationSuite(
            name="bronze_pagamentos",
            table_name="nessie.bronze.pagamentos",
            expectations=(
                ExpectationDefinition("expect_table_row_count_to_be_greater_than", {"value": 100}, critical=True),
                ExpectationDefinition("expect_column_values_to_not_be_null", {"column": "cod_pagamento"}, critical=True),
            ),
        ),
    )


def build_silver_suites() -> tuple[ValidationSuite, ...]:
    return (
        ValidationSuite(
            name="silver_notas_operacionais",
            table_name="nessie.silver.notas_operacionais",
            expectations=(
                ExpectationDefinition("expect_column_values_to_not_be_null", {"column": "cod_nota"}, critical=True),
                ExpectationDefinition("expect_column_values_to_not_be_null", {"column": "classificacao_acf_asf"}, critical=True),
                ExpectationDefinition(
                    "expect_column_values_to_be_in_set",
                    {
                        "column": "classificacao_acf_asf",
                        "value_set": ["ACF_A", "ACF_B", "ACF_C", "ASF_RISCO", "ASF_FORA_RISCO"],
                    },
                    critical=True,
                ),
                ExpectationDefinition(
                    "expect_column_values_to_be_in_set",
                    {
                        "column": "status_atraso",
                        "value_set": ["NO_PRAZO", "ATRASADO", "PENDENTE_NO_PRAZO", "PENDENTE_FORA_PRAZO"],
                    },
                    critical=True,
                ),
            ),
        ),
        ValidationSuite(
            name="silver_entregas_fatura",
            table_name="nessie.silver.entregas_fatura",
            expectations=(
                ExpectationDefinition("expect_column_values_to_be_between", {"column": "distancia_metros", "min_value": 0, "max_value": 50000}),
                ExpectationDefinition("expect_column_values_to_not_be_null", {"column": "cod_entrega"}, critical=True),
            ),
        ),
        ValidationSuite(
            name="silver_pagamentos",
            table_name="nessie.silver.pagamentos",
            expectations=(
                ExpectationDefinition("expect_column_values_to_not_be_null", {"column": "cod_pagamento"}, critical=True),
                ExpectationDefinition("expect_column_values_to_be_between", {"column": "valor_fatura", "min_value": 0.01}, critical=True),
            ),
        ),
    )


def build_default_checkpoints() -> tuple[CheckpointDefinition, ...]:
    return (
        CheckpointDefinition("checkpoint_bronze_daily", build_bronze_suites()),
        CheckpointDefinition("checkpoint_silver_daily", build_silver_suites()),
    )
