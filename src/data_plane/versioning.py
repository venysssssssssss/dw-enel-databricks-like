"""Dataset versioning primitives shared by BI, API cache and RAG."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    """Content-addressed version for every dataset-dependent view."""

    hash: str
    sources: tuple[str, ...]
    generated_at: str

    @classmethod
    def from_paths(cls, paths: tuple[Path, ...]) -> DatasetVersion:
        existing = tuple(path for path in paths if path.exists())
        digests = [_file_digest(path) for path in existing]
        payload = {
            "sources": [str(path) for path in existing],
            "digests": digests,
        }
        version_hash = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()
        return cls(
            hash=version_hash,
            sources=tuple(str(path) for path in existing),
            generated_at=datetime.now(UTC).isoformat(),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def publish(self, *, channel: str = "enel:dataset") -> None:
        """Best-effort Redis publish used to cascade cache invalidation."""
        try:
            import redis
        except ImportError:
            return
        try:
            client = redis.Redis.from_url("redis://localhost:6379/0")
            client.publish(channel, _stable_json(self.as_dict()))
        except Exception:
            return


def _file_digest(path: Path, *, chunk_size: int = 1024 * 1024) -> dict[str, Any]:
    hasher = hashlib.sha256()
    stat = path.stat()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            hasher.update(chunk)
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": hasher.hexdigest(),
    }


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
