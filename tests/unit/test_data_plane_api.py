from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import create_app
from src.api.routers import dashboard, rag
from src.data_plane.versioning import DatasetVersion


def _filters_param(value: dict[str, Any]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(value).encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


class FakeDataStore:
    def version(self) -> DatasetVersion:
        return DatasetVersion(
            hash="dataset-123",
            sources=("silver.csv",),
            generated_at="2026-01-01T00:00:00Z",
        )

    def aggregate_records(
        self,
        view_id: str,
        filters: dict[str, Any] | None = None,
        *,
        include_total: bool = False,
    ) -> list[dict[str, Any]]:
        if view_id == "missing":
            raise KeyError("View desconhecida: missing")
        return [{"view_id": view_id, "filters": filters or {}, "include_total": include_total}]

    def cards(self) -> list[Any]:
        return [
            SimpleNamespace(
                chunk_id="card-1",
                section="Visão geral",
                dataset_version="dataset-123",
                anchor="visao-geral",
                token_count=42,
            )
        ]


@pytest_asyncio.fixture()
async def data_plane_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(dashboard, "DataStore", FakeDataStore)
    monkeypatch.setattr(rag, "DataStore", FakeDataStore)
    app = create_app(
        enable_lifespan=False,
        enable_rate_limit=False,
        enable_observability=False,
        enable_middlewares=False,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_dataset_version_endpoint(data_plane_client: AsyncClient) -> None:
    response = await data_plane_client.get("/v1/dataset/version")

    assert response.status_code == 200
    assert response.json() == {
        "hash": "dataset-123",
        "sources": ["silver.csv"],
        "generated_at": "2026-01-01T00:00:00Z",
    }


@pytest.mark.asyncio
async def test_aggregation_endpoint_decodes_filters_and_supports_304(
    data_plane_client: AsyncClient,
) -> None:
    filters = {"regiao": ["CE"], "status": "ABERTO"}
    response = await data_plane_client.get(
        "/v1/aggregations/overview",
        params={"filters": _filters_param(filters)},
    )

    assert response.status_code == 200
    assert response.headers["x-cache"] == "MISS"
    assert response.headers["etag"].startswith('"dataset-123:')
    assert response.json()["filters"] == filters
    assert response.json()["data"][0]["view_id"] == "overview"

    warm = await data_plane_client.get(
        "/v1/aggregations/overview",
        params={"filters": _filters_param(filters)},
    )

    assert warm.status_code == 200
    assert warm.headers["x-cache"] == "HIT"

    cached = await data_plane_client.get(
        "/v1/aggregations/overview",
        params={"filters": _filters_param(filters)},
        headers={"If-None-Match": response.headers["etag"]},
    )

    assert cached.status_code == 304
    assert not cached.content


@pytest.mark.asyncio
async def test_aggregation_endpoint_rejects_invalid_filters(
    data_plane_client: AsyncClient,
) -> None:
    response = await data_plane_client.get(
        "/v1/aggregations/overview",
        params={"filters": "not-json"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_aggregation_endpoint_maps_unknown_view_to_404(
    data_plane_client: AsyncClient,
) -> None:
    response = await data_plane_client.get("/v1/aggregations/missing")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rag_cards_endpoint_uses_dataset_version(data_plane_client: AsyncClient) -> None:
    response = await data_plane_client.get("/v1/rag/cards")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset_hash"] == "dataset-123"
    assert payload["cards"] == [
        {
            "id": "card-1",
            "title": "Visão geral",
            "hash": "dataset-123",
            "anchor": "visao-geral",
            "token_count": 42,
        }
    ]


@pytest.mark.asyncio
async def test_rag_stream_rejects_stale_dataset_version(data_plane_client: AsyncClient) -> None:
    response = await data_plane_client.post(
        "/v1/rag/stream",
        json={"question": "Qual a taxa de refaturamento?"},
        headers={"X-Dataset-Version": "old"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["current_dataset_version"] == "dataset-123"


@pytest.mark.asyncio
async def test_web_vitals_endpoint_accepts_metrics(data_plane_client: AsyncClient) -> None:
    response = await data_plane_client.post(
        "/v1/telemetry/web-vitals",
        json={"name": "LCP", "value": 1234.5, "rating": "good"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
