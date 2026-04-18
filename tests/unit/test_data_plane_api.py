from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

if TYPE_CHECKING:
    from pathlib import Path

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
async def test_rag_stream_forwards_history_to_stream_service(
    data_plane_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_stream(request_obj, *, orchestrator=None):  # noqa: ANN001
        captured["history"] = request_obj.history
        captured["orchestrator"] = orchestrator
        yield "event: done\ndata: {\"ok\": true}\n\n"

    monkeypatch.setattr(rag, "stream_rag_events", fake_stream)
    monkeypatch.setattr(rag, "get_rag_orchestrator", lambda app=None: "orch-singleton")
    response = await data_plane_client.post(
        "/v1/rag/stream",
        json={
            "question": "Pergunta de follow-up",
            "history": [
                {"role": "user", "content": "Qual a taxa em CE?"},
                {"role": "assistant", "content": "A taxa é 11,8%."},
            ],
        },
        headers={"X-Dataset-Version": "dataset-123"},
    )
    assert response.status_code == 200
    await response.aread()
    assert captured["history"] == [
        {"role": "user", "content": "Qual a taxa em CE?"},
        {"role": "assistant", "content": "A taxa é 11,8%."},
    ]
    assert captured["orchestrator"] == "orch-singleton"


def test_rag_dataset_version_cache_reuses_hash_when_fingerprint_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_path = tmp_path / "silver.csv"
    file_path.write_text("a,b\n1,2\n", encoding="utf-8")

    class CountingStore:
        silver_path = file_path
        topic_assignments_path = tmp_path / "missing.csv"
        topic_taxonomy_path = tmp_path / "missing.json"
        medidor_sp_path = tmp_path / "missing_medidor.csv"
        fatura_sp_path = tmp_path / "missing_fatura.xlsx"

        def __init__(self) -> None:
            self.calls = 0

        def version(self) -> DatasetVersion:
            self.calls += 1
            return DatasetVersion(
                hash="dataset-abc",
                sources=(str(self.silver_path),),
                generated_at="2026-01-01T00:00:00Z",
            )

    monkeypatch.setenv("RAG_DATASET_VERSION_CACHE_TTL_SEC", "30")
    rag._DATASET_VERSION_CACHE.dataset_hash = ""
    rag._DATASET_VERSION_CACHE.fingerprint = ()
    rag._DATASET_VERSION_CACHE.ts = 0.0
    store = CountingStore()

    first = rag._current_dataset_hash(store)
    second = rag._current_dataset_hash(store)

    assert first == "dataset-abc"
    assert second == "dataset-abc"
    assert store.calls == 1


@pytest.mark.asyncio
async def test_web_vitals_endpoint_accepts_metrics(data_plane_client: AsyncClient) -> None:
    response = await data_plane_client.post(
        "/v1/telemetry/web-vitals",
        json={"name": "LCP", "value": 1234.5, "rating": "good"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
