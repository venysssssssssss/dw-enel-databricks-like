"""Best-effort cache helpers for API/data-plane responses."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    value: bytes
    created_at: float


class MemoryResponseCache:
    def __init__(self, *, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}

    def get(self, key: str) -> bytes | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if time.monotonic() - entry.created_at > self.ttl_seconds:
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: bytes) -> None:
        self._entries[key] = CacheEntry(value=value, created_at=time.monotonic())

    def clear(self) -> None:
        self._entries.clear()


def cache_key(*parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
