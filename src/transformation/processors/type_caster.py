"""Helpers to cast Bronze string columns into typed Silver columns."""

from __future__ import annotations

from src.common.contracts import ColumnDefinition


def apply_schema_types(df, schema_config: list[ColumnDefinition]):
    from pyspark.sql.functions import col, regexp_replace, to_date, to_timestamp

    typed_df = df
    for column_config in schema_config:
        column_name = column_config.name
        target_type = column_config.type.lower()
        if column_name not in typed_df.columns:
            continue
        if target_type.startswith("date"):
            typed_df = typed_df.withColumn(column_name, to_date(col(column_name), "dd/MM/yyyy"))
        elif target_type.startswith("timestamp"):
            typed_df = typed_df.withColumn(column_name, to_timestamp(col(column_name), "dd/MM/yyyy HH:mm:ss"))
        elif target_type.startswith("decimal"):
            typed_df = typed_df.withColumn(
                column_name,
                regexp_replace(col(column_name), ",", ".").cast(target_type),
            )
        elif target_type == "boolean":
            typed_df = typed_df.withColumn(column_name, col(column_name).cast("boolean"))
        else:
            typed_df = typed_df.withColumn(column_name, col(column_name).cast(target_type))
    return typed_df
