"""API settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ENEL_",
        extra="ignore",
    )

    app_name: str = "ENEL Analytics Platform API"
    app_version: str = "1.0.0"
    secret_key: str = "replace-me"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    token_expire_minutes: int = 30
    rate_limit_default: str = "60/minute"

    trino_host: str = "localhost"
    trino_port: int = 8443
    trino_catalog: str = "iceberg"
    trino_schema: str = "gold"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_exports_bucket: str = "exports"

    model_registry_path: str = "data/model_registry"


@lru_cache(maxsize=1)
def get_api_settings() -> APISettings:
    return APISettings()
