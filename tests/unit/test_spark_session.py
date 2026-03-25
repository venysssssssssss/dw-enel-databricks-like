from __future__ import annotations

from src.common.spark_session import build_spark_config


def test_spark_config_contains_local_optimizations() -> None:
    config = build_spark_config()
    assert config["spark.master"] == "local[4]"
    assert config["spark.sql.shuffle.partitions"] == "8"
    assert config["spark.sql.adaptive.enabled"] == "true"
