from __future__ import annotations

from pathlib import Path

from src.common.minio_client import MinIOClient


class FakeBotoClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def head_bucket(self, **kwargs):
        self.calls.append(("head_bucket", tuple(), kwargs))

    def create_bucket(self, **kwargs):
        self.calls.append(("create_bucket", tuple(), kwargs))

    def upload_file(self, *args, **kwargs):
        self.calls.append(("upload_file", args, kwargs))

    def download_file(self, *args, **kwargs):
        self.calls.append(("download_file", args, kwargs))

    def generate_presigned_url(self, *args, **kwargs):
        self.calls.append(("generate_presigned_url", args, kwargs))
        return "http://signed-url"

    def get_paginator(self, _name):
        return self

    def paginate(self, **_kwargs):
        return [{"Contents": [{"Key": "a"}, {"Key": "b"}]}]

    def head_object(self, **kwargs):
        self.calls.append(("head_object", tuple(), kwargs))


def test_minio_client_wrapper(monkeypatch, tmp_path: Path) -> None:
    fake_client = FakeBotoClient()
    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: fake_client)
    client = MinIOClient(endpoint="http://localhost:9000", access_key="x", secret_key="y")
    client.ensure_bucket("lakehouse")
    client.upload_file(tmp_path / "file.txt", "lakehouse", "key")
    assert client.list_objects("lakehouse") == ["a", "b"]
    assert client.get_presigned_url("lakehouse", "key") == "http://signed-url"
