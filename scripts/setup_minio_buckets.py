"""Create required MinIO buckets for the platform."""

from __future__ import annotations

from src.common.config import get_settings
from src.common.minio_client import MinIOClient


def main() -> int:
    settings = get_settings()
    client = MinIOClient()
    buckets = [
        settings.minio_bucket_lakehouse,
        settings.minio_bucket_ml_artifacts,
        settings.minio_bucket_airflow_logs,
        settings.minio_bucket_exports,
    ]
    for bucket in buckets:
        client.ensure_bucket(bucket)
        print(bucket)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
