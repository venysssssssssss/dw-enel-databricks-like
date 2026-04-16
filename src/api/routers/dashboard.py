"""Unified dashboard/data-plane API routes."""

from __future__ import annotations

import base64
import json
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import StreamingResponse

from src.data_plane import DataStore
from src.data_plane.cache import MemoryResponseCache, cache_key

router = APIRouter()
_AGGREGATION_CACHE = MemoryResponseCache(ttl_seconds=300)

try:  # pragma: no cover - exercised through /metrics in deployed API.
    from prometheus_client import Counter, Histogram

    CACHE_EVENTS = Counter(
        "enel_cache_events_total",
        "Cache hits/misses by layer and route.",
        ("layer", "route", "result"),
    )
    AGGREGATION_LATENCY = Histogram(
        "enel_aggregation_latency_seconds",
        "Data-plane aggregation latency by view and cache result.",
        ("view_id", "cache_result"),
    )
    WEB_VITALS = Histogram(
        "enel_web_vital_value",
        "Frontend web-vitals reported by the React SPA.",
        ("name", "rating"),
    )
except Exception:  # pragma: no cover - prometheus optional in lean installs.
    CACHE_EVENTS = None
    AGGREGATION_LATENCY = None
    WEB_VITALS = None


@router.get("/dataset/version")
def dataset_version() -> dict[str, Any]:
    return DataStore().version().as_dict()


@router.get("/aggregations/{view_id}")
def aggregation(
    view_id: str,
    response: Response,
    filters: str | None = None,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
) -> Response:
    store = DataStore()
    parsed_filters = _parse_filters(filters)
    version = store.version()
    etag = f"\"{version.hash}:{cache_key(parsed_filters)}\""
    cache_id = cache_key("aggregation", view_id, version.hash, parsed_filters)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "max-age=60, stale-while-revalidate=300"
    if if_none_match == etag:
        _observe_cache("http", "aggregation", "not_modified")
        response.status_code = 304
        return response
    cached = _AGGREGATION_CACHE.get(cache_id)
    if cached is not None:
        _observe_cache("memory", "aggregation", "hit")
        return Response(
            content=cached,
            media_type="application/json",
            headers={
                "ETag": etag,
                "Cache-Control": "max-age=60, stale-while-revalidate=300",
                "X-Cache": "HIT",
            },
        )
    _observe_cache("memory", "aggregation", "miss")
    try:
        records = store.aggregate_records(view_id, parsed_filters)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload = json.dumps(
        {
            "view_id": view_id,
            "dataset_hash": version.hash,
            "filters": parsed_filters,
            "data": records,
        },
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    _AGGREGATION_CACHE.set(cache_id, payload)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "ETag": etag,
            "Cache-Control": "max-age=60, stale-while-revalidate=300",
            "X-Cache": "MISS",
        },
    )


@router.get("/dataset/erro-leitura.arrow")
def erro_leitura_arrow() -> StreamingResponse:
    try:
        import pyarrow as pa
        import pyarrow.ipc as ipc
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="pyarrow não instalado; instale a dependência para servir Arrow IPC.",
        ) from exc
    frame = DataStore().load_silver(include_total=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    sink = pa.BufferOutputStream()
    with ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    payload = sink.getvalue().to_pybytes()
    return StreamingResponse(
        iter([payload]),
        media_type="application/vnd.apache.arrow.stream",
        headers={"Cache-Control": "max-age=60, stale-while-revalidate=300"},
    )


@router.post("/telemetry/web-vitals")
def web_vitals(payload: dict[str, Any]) -> dict[str, bool]:
    name = str(payload.get("name", "unknown"))[:80]
    rating = str(payload.get("rating", "unknown"))[:40]
    value = _float_or_zero(payload.get("value"))
    if WEB_VITALS is not None:
        WEB_VITALS.labels(name=name, rating=rating).observe(value)
    return {"ok": True}


def _parse_filters(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        decoded = base64.urlsafe_b64decode(_pad_base64(raw)).decode("utf-8")
        value = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="filters deve ser base64url(JSON).") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail="filters deve decodificar para objeto JSON.")
    return value


def _pad_base64(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode("ascii")


def _observe_cache(layer: str, route: str, result: str) -> None:
    if CACHE_EVENTS is not None:
        CACHE_EVENTS.labels(layer=layer, route=route, result=result).inc()


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
