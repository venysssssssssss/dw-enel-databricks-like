"""Factory for SparkSession configured for the local ENEL platform environment."""

from __future__ import annotations

from collections.abc import Mapping

from src.common.config import get_settings


def build_spark_config(
    app_name: str = "enel-platform",
    memory: str | None = None,
    *,
    iceberg_enabled: bool = True,
) -> dict[str, str]:
    settings = get_settings()
    resolved_memory = memory or settings.spark_driver_memory
    config: dict[str, str] = {
        "spark.app.name": app_name,
        "spark.master": settings.spark_master,
        "spark.driver.memory": resolved_memory,
        "spark.sql.shuffle.partitions": str(settings.spark_shuffle_partitions),
        "spark.default.parallelism": str(settings.spark_default_parallelism),
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
        "spark.sql.adaptive.skewJoin.enabled": "true",
        "spark.sql.parquet.compression.codec": "zstd",
        "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
        "spark.hadoop.fs.s3a.endpoint": settings.minio_endpoint_url,
        "spark.hadoop.fs.s3a.access.key": settings.minio_access_key,
        "spark.hadoop.fs.s3a.secret.key": settings.minio_secret_key,
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
    }
    if iceberg_enabled:
        config.update(
            {
                "spark.sql.catalog.nessie": "org.apache.iceberg.spark.SparkCatalog",
                "spark.sql.catalog.nessie.catalog-impl": "org.apache.iceberg.nessie.NessieCatalog",
                "spark.sql.catalog.nessie.uri": settings.nessie_uri,
                "spark.sql.catalog.nessie.ref": settings.nessie_ref,
                "spark.sql.catalog.nessie.warehouse": f"s3a://{settings.minio_bucket_lakehouse}/",
                "spark.sql.catalog.nessie.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
                "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
            }
        )
    return config


def create_spark_session(
    app_name: str = "enel-platform",
    memory: str | None = None,
    *,
    iceberg_enabled: bool = True,
    extra_configs: Mapping[str, str] | None = None,
):
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PySpark não está instalado. Instale com `pip install -e \".[platform]\"`."
        ) from exc

    config = build_spark_config(app_name=app_name, memory=memory, iceberg_enabled=iceberg_enabled)
    if extra_configs:
        config.update(dict(extra_configs))

    builder = SparkSession.builder
    for key, value in config.items():
        builder = builder.config(key, value)
    return builder.getOrCreate()
