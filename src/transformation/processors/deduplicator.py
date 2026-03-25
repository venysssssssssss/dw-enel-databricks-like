"""Deduplication helpers based on Spark window functions."""

from __future__ import annotations


def deduplicate(df, *, keys: list[str], order_col: str, ascending: bool = False):
    from pyspark.sql.functions import col, row_number
    from pyspark.sql.window import Window

    window = Window.partitionBy(*keys).orderBy(col(order_col).asc() if ascending else col(order_col).desc())
    return df.withColumn("_row_num", row_number().over(window)).filter("`_row_num` = 1").drop("_row_num")
