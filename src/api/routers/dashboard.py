"""Unified dashboard/data-plane API routes."""

from __future__ import annotations

import base64
import json
import time
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import StreamingResponse

from src.data_plane import DataStore
from src.data_plane.cache import MemoryResponseCache, cache_key

router = APIRouter()
_AGGREGATION_CACHE = MemoryResponseCache(ttl_seconds=300)

# Bump when any aggregation handler logic changes — invalidates client ETag/sessionStorage cache.
DATA_PLANE_VIEW_VERSION = "v4-descricoes-fallback"

try:  # pragma: no cover - exercised through /metrics in deployed API.
    from prometheus_client import Counter, Gauge, Histogram

    CACHE_EVENTS = Counter(
        "enel_cache_events_total",
        "Cache hits/misses by layer, route and aggregation view.",
        ("layer", "route", "result", "view_id"),
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
    SEVERITY_SP_TOTAL = Gauge(
        "enel_severity_sp_total",
        "Latest SP severity total complaints exposed by overview aggregations.",
        ("severity",),
    )
    CLASSIFIER_INDEFINIDO_RATIO = Gauge(
        "enel_classifier_indefinido_ratio",
        "Latest classifier indefinido ratio by region.",
        ("regiao",),
    )
except Exception:  # pragma: no cover - prometheus optional in lean installs.
    CACHE_EVENTS = None
    AGGREGATION_LATENCY = None
    WEB_VITALS = None
    SEVERITY_SP_TOTAL = None
    CLASSIFIER_INDEFINIDO_RATIO = None


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
    started = time.perf_counter()
    store = DataStore()
    parsed_filters = _parse_filters(filters)
    version = store.version()
    etag = f"\"{version.hash}:{DATA_PLANE_VIEW_VERSION}:{cache_key(parsed_filters)}\""
    cache_id = cache_key("aggregation", DATA_PLANE_VIEW_VERSION, view_id, version.hash, parsed_filters)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "max-age=60, stale-while-revalidate=300"
    if if_none_match == etag:
        _observe_cache("http", "aggregation", "not_modified", view_id)
        _observe_latency(view_id, "not_modified", started)
        response.status_code = 304
        return response
    cached = _AGGREGATION_CACHE.get(cache_id)
    if cached is not None:
        _observe_cache("memory", "aggregation", "hit", view_id)
        _observe_latency(view_id, "hit", started)
        return Response(
            content=cached,
            media_type="application/json",
            headers={
                "ETag": etag,
                "Cache-Control": "max-age=60, stale-while-revalidate=300",
                "X-Cache": "HIT",
            },
        )
    _observe_cache("memory", "aggregation", "miss", view_id)
    try:
        records = store.aggregate_records(view_id, parsed_filters)
    except KeyError as exc:
        _observe_latency(view_id, "error", started)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _observe_severity_total(view_id, records)
    _observe_classifier_coverage(view_id, records)
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
    _observe_latency(view_id, "miss", started)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "ETag": etag,
            "Cache-Control": "max-age=60, stale-while-revalidate=300",
            "X-Cache": "MISS",
        },
    )


_SEVERITY_DESCRICOES_VIEW = {
    "alta": "sp_severidade_alta_descricoes",
    "critica": "sp_severidade_critica_descricoes",
    "demais": "sp_severidade_demais_descricoes",
}


@router.get("/severidade/{level}/descricoes")
def severidade_descricoes(
    level: str,
    response: Response,
    limit: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
) -> Response:
    """Dedicated endpoint for the assistant-identified descrições table.

    Returns a deterministic top-N of cleaned silver rows for the requested
    severity (alta|critica) on SP, enriched with action suggestions, owning
    area and top-10 reincident installations per causa canônica. Bypasses the
    generic aggregations cache so changes to the descrição handler are picked
    up immediately by the React SPA.
    """
    started = time.perf_counter()
    view_id = _SEVERITY_DESCRICOES_VIEW.get(level)
    if view_id is None:
        raise HTTPException(status_code=404, detail=f"Severidade desconhecida: {level}")
    capped = max(1, min(int(limit), 50))
    period_filters: dict[str, Any] = {}
    if start_date:
        period_filters["start_date"] = start_date
    if end_date:
        period_filters["end_date"] = end_date

    store = DataStore()
    version = store.version()
    period_tag = f"{start_date or '-'}:{end_date or '-'}"
    etag = (
        f"\"{version.hash}:{DATA_PLANE_VIEW_VERSION}:descricoes:{level}:{capped}:{period_tag}\""
    )
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "max-age=30, stale-while-revalidate=120"
    if if_none_match == etag:
        _observe_cache("http", "descricoes", "not_modified", view_id)
        _observe_latency(view_id, "not_modified", started)
        response.status_code = 304
        return response

    cache_id = cache_key(
        "descricoes",
        DATA_PLANE_VIEW_VERSION,
        level,
        capped,
        period_tag,
        version.hash,
    )
    cached = _AGGREGATION_CACHE.get(cache_id)
    if cached is not None:
        _observe_cache("memory", "descricoes", "hit", view_id)
        _observe_latency(view_id, "hit", started)
        return Response(
            content=cached,
            media_type="application/json",
            headers={
                "ETag": etag,
                "Cache-Control": "max-age=30, stale-while-revalidate=120",
                "X-Cache": "HIT",
            },
        )

    _observe_cache("memory", "descricoes", "miss", view_id)
    try:
        records = store.aggregate_records(view_id, period_filters)
    except KeyError as exc:
        _observe_latency(view_id, "error", started)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    records = records[:capped]
    payload = json.dumps(
        {
            "view_id": view_id,
            "dataset_hash": version.hash,
            "severidade": level,
            "limit": capped,
            "count": len(records),
            "data": records,
        },
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    _AGGREGATION_CACHE.set(cache_id, payload)
    _observe_latency(view_id, "miss", started)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "ETag": etag,
            "Cache-Control": "max-age=30, stale-while-revalidate=120",
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


def _observe_cache(layer: str, route: str, result: str, view_id: str = "all") -> None:
    if CACHE_EVENTS is not None:
        CACHE_EVENTS.labels(layer=layer, route=route, result=result, view_id=view_id).inc()


def _observe_latency(view_id: str, cache_result: str, started: float) -> None:
    if AGGREGATION_LATENCY is not None:
        AGGREGATION_LATENCY.labels(view_id=view_id, cache_result=cache_result).observe(
            time.perf_counter() - started
        )


def _observe_severity_total(view_id: str, records: list[dict[str, Any]]) -> None:
    if SEVERITY_SP_TOTAL is None or not records:
        return
    severity = {
        "sp_severidade_alta_overview": "alta",
        "sp_severidade_critica_overview": "critica",
    }.get(view_id)
    if severity is None:
        return
    try:
        total = float(records[0].get("total", 0))
    except (TypeError, ValueError):
        total = 0.0
    SEVERITY_SP_TOTAL.labels(severity=severity).set(total)


def _observe_classifier_coverage(view_id: str, records: list[dict[str, Any]]) -> None:
    if CLASSIFIER_INDEFINIDO_RATIO is None or view_id != "classifier_coverage":
        return
    for row in records:
        regiao = str(row.get("regiao", "NAO_INFORMADA"))
        try:
            ratio = float(row.get("indefinido_pct", 0))
        except (TypeError, ValueError):
            ratio = 0.0
        CLASSIFIER_INDEFINIDO_RATIO.labels(regiao=regiao).set(ratio)


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
