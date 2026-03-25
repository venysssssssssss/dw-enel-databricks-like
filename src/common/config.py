"""Centralized configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ENEL_",
        extra="ignore",
    )

    environment: str = "dev"
    project_root: Path = Path(".")
    log_level: str = "INFO"
    log_json: bool = False

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio123"
    minio_secure: bool = False
    minio_bucket_lakehouse: str = "lakehouse"
    minio_bucket_ml_artifacts: str = "ml-artifacts"
    minio_bucket_airflow_logs: str = "airflow-logs"
    minio_bucket_exports: str = "exports"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "enel"
    postgres_password: str = "enel123"
    postgres_database: str = "postgres"

    nessie_uri: str = "http://localhost:19120/api/v2"
    nessie_ref: str = "main"
    trino_host: str = "localhost"
    trino_port: int = 8443
    trino_catalog: str = "iceberg"
    trino_schema: str = "bronze"

    spark_master: str = "local[4]"
    spark_driver_memory: str = "4g"
    spark_shuffle_partitions: int = 8
    spark_default_parallelism: int = 8

    data_raw_dir: Path = Field(default=Path("data/raw"))
    data_sample_dir: Path = Field(default=Path("data/sample"))
    data_feature_store_dir: Path = Field(default=Path("data/feature_store"))
    data_model_registry_dir: Path = Field(default=Path("data/model_registry"))
    data_scores_dir: Path = Field(default=Path("data/gold/scores"))
    data_monitoring_dir: Path = Field(default=Path("data/monitoring"))
    audit_namespace: str = "nessie.audit"
    mlflow_tracking_uri: str = "http://localhost:5000"
    ml_use_native_boosters: bool = False
    mlflow_tracking_enabled: bool = False
    mlflow_experiments: list[str] = Field(
        default_factory=lambda: [
            "enel-atraso-entrega",
            "enel-inadimplencia",
            "enel-metas",
            "enel-anomalias",
        ]
    )

    @property
    def project_root_path(self) -> Path:
        return self.project_root.resolve()

    @property
    def raw_data_path(self) -> Path:
        return (self.project_root_path / self.data_raw_dir).resolve()

    @property
    def sample_data_path(self) -> Path:
        return (self.project_root_path / self.data_sample_dir).resolve()

    @property
    def feature_store_path(self) -> Path:
        return (self.project_root_path / self.data_feature_store_dir).resolve()

    @property
    def model_registry_path(self) -> Path:
        return (self.project_root_path / self.data_model_registry_dir).resolve()

    @property
    def scores_path(self) -> Path:
        return (self.project_root_path / self.data_scores_dir).resolve()

    @property
    def monitoring_path(self) -> Path:
        return (self.project_root_path / self.data_monitoring_dir).resolve()

    @property
    def minio_endpoint_url(self) -> str:
        protocol = "https" if self.minio_secure else "http"
        if self.minio_endpoint.startswith("http"):
            return self.minio_endpoint
        return f"{protocol}://{self.minio_endpoint}"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )


@lru_cache(maxsize=1)
def get_settings() -> PlatformSettings:
    return PlatformSettings()
