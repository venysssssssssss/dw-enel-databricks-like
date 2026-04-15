"""Lightweight cache primitives for dashboard aggregations."""

from __future__ import annotations

import hashlib
import json
import pickle
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

import pandas as pd

T = TypeVar("T")

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class FrameSignature:
    rows: int
    columns: tuple[str, ...]
    dtypes: tuple[str, ...]
    head_sha256: str

    def as_key(self) -> str:
        payload = {
            "rows": self.rows,
            "columns": self.columns,
            "dtypes": self.dtypes,
            "head_sha256": self.head_sha256,
        }
        return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


@dataclass(slots=True)
class _CacheEntry:
    created_at: float
    value: Any


_MEMORY_CACHE: dict[str, _CacheEntry] = {}


def frame_fingerprint(frame: pd.DataFrame, *, sample_rows: int = 128) -> FrameSignature:
    """Create a cheap content-aware signature without serializing the full frame."""
    sample = pd.concat([frame.head(sample_rows), frame.tail(sample_rows)]).drop_duplicates()
    sample_bytes = sample.to_csv(index=False).encode("utf-8", errors="ignore")
    return FrameSignature(
        rows=int(len(frame)),
        columns=tuple(map(str, frame.columns)),
        dtypes=tuple(map(str, frame.dtypes)),
        head_sha256=hashlib.sha256(sample_bytes).hexdigest(),
    )


def path_fingerprint(path: Path, *, head_bytes: int = 8 * 1024 * 1024) -> str:
    """Fingerprint a file using size, mtime and first bytes for fast invalidation."""
    if not path.exists():
        return "missing"
    stat = path.stat()
    with path.open("rb") as handle:
        head = handle.read(head_bytes)
    payload = {
        "path": str(path),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "head_sha256": hashlib.sha256(head).hexdigest(),
    }
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def filters_hash(filters: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json(filters).encode("utf-8")).hexdigest()


def cached_aggregation(
    func: Callable[..., T],
    frame: pd.DataFrame,
    *,
    ttl_seconds: int = 3600,
    **kwargs: Any,
) -> T:
    """Cache deterministic dataframe aggregations by function, frame and kwargs."""
    key_payload = {
        "func": f"{func.__module__}.{func.__qualname__}",
        "frame": frame_fingerprint(frame).as_key(),
        "kwargs": kwargs,
    }
    key = hashlib.sha256(_stable_json(key_payload).encode("utf-8")).hexdigest()
    now = time.monotonic()
    entry = _MEMORY_CACHE.get(key)
    if entry and now - entry.created_at <= ttl_seconds:
        return _copy_if_dataframe(entry.value)
    value = func(frame, **kwargs)
    _MEMORY_CACHE[key] = _CacheEntry(now, _copy_if_dataframe(value))
    return _copy_if_dataframe(value)


def clear_memory_cache() -> None:
    _MEMORY_CACHE.clear()


def disk_cache_path(cache_dir: Path, namespace: str, signature: str) -> Path:
    safe_namespace = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in namespace)
    return cache_dir / f"{safe_namespace}_{signature}.pkl"


def load_or_build_disk_cache(
    cache_dir: Path,
    namespace: str,
    signature: str,
    builder: Callable[[], T],
) -> T:
    """Load a pickle artifact or build it atomically enough for local dashboards."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = disk_cache_path(cache_dir, namespace, signature)
    if path.exists():
        with path.open("rb") as handle:
            return pickle.load(handle)
    value = builder()
    tmp = path.with_suffix(".tmp")
    with tmp.open("wb") as handle:
        pickle.dump(value, handle)
    tmp.replace(path)
    return value


def _copy_if_dataframe(value: T) -> T:
    if isinstance(value, pd.DataFrame):
        return value.copy()  # type: ignore[return-value]
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
