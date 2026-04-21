"""Unified analytical data plane for BI and RAG surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.data_plane.store import DataStore
    from src.data_plane.versioning import DatasetVersion


def __getattr__(name: str) -> object:
    if name == "DataStore":
        from src.data_plane.store import DataStore

        return DataStore
    if name == "DatasetVersion":
        from src.data_plane.versioning import DatasetVersion

        return DatasetVersion
    raise AttributeError(f"module 'src.data_plane' has no attribute {name!r}")

__all__ = ["DataStore", "DatasetVersion"]
