"""Thin MinIO client wrapper for storage operations."""

from __future__ import annotations

from pathlib import Path

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from src.common.config import get_settings


class MinIOClient:
    """Abstraction over boto3 to keep storage interactions explicit and testable."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        *,
        secure: bool | None = None,
    ) -> None:
        settings = get_settings()
        resolved_endpoint = endpoint or settings.minio_endpoint
        resolved_secure = settings.minio_secure if secure is None else secure
        if not resolved_endpoint.startswith("http"):
            protocol = "https" if resolved_secure else "http"
            resolved_endpoint = f"{protocol}://{resolved_endpoint}"

        self._client: BaseClient = boto3.client(
            "s3",
            endpoint_url=resolved_endpoint,
            aws_access_key_id=access_key or settings.minio_access_key,
            aws_secret_access_key=secret_key or settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
        )

    def ensure_bucket(self, bucket: str) -> None:
        if not self.bucket_exists(bucket):
            self._client.create_bucket(Bucket=bucket)

    def bucket_exists(self, bucket: str) -> bool:
        try:
            self._client.head_bucket(Bucket=bucket)
        except ClientError:
            return False
        return True

    def upload_file(self, local_path: Path, bucket: str, key: str) -> None:
        self._client.upload_file(str(local_path), bucket, key)

    def download_file(self, bucket: str, key: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(bucket, key, str(local_path))

    def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        objects: list[str] = []
        for page in pages:
            for item in page.get("Contents", []):
                objects.append(str(item["Key"]))
        return objects

    def file_exists(self, bucket: str, key: str) -> bool:
        try:
            self._client.head_object(Bucket=bucket, Key=key)
        except ClientError:
            return False
        return True

    def get_presigned_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        return str(
            self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires,
            )
        )
