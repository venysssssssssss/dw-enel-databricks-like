from __future__ import annotations

import time

import pandas as pd

from src.viz.cache import (
    cached_aggregation,
    clear_memory_cache,
    disk_cache_path,
    filters_hash,
    frame_fingerprint,
    load_or_build_disk_cache,
    path_fingerprint,
)


def test_frame_fingerprint_changes_when_content_changes() -> None:
    left = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    right = pd.DataFrame({"a": [1, 3], "b": ["x", "y"]})

    assert frame_fingerprint(left).as_key() != frame_fingerprint(right).as_key()


def test_filters_hash_is_ordered_and_stable() -> None:
    assert filters_hash({"b": 2, "a": 1}) == filters_hash({"a": 1, "b": 2})
    assert filters_hash({"a": 1}) != filters_hash({"a": 2})


def test_cached_aggregation_reuses_value_and_returns_dataframe_copy() -> None:
    clear_memory_cache()
    calls = {"count": 0}
    frame = pd.DataFrame({"grupo": ["A", "A", "B"], "valor": [1, 2, 3]})

    def aggregate(data: pd.DataFrame, *, multiplier: int = 1) -> pd.DataFrame:
        calls["count"] += 1
        return data.groupby("grupo", as_index=False)["valor"].sum().assign(
            valor=lambda df: df["valor"] * multiplier
        )

    first = cached_aggregation(aggregate, frame, multiplier=2)
    first.loc[0, "valor"] = 999
    second = cached_aggregation(aggregate, frame, multiplier=2)

    assert calls["count"] == 1
    assert second.loc[0, "valor"] == 6


def test_cached_aggregation_expires_by_ttl() -> None:
    clear_memory_cache()
    calls = {"count": 0}
    frame = pd.DataFrame({"valor": [1]})

    def aggregate(data: pd.DataFrame) -> pd.DataFrame:
        calls["count"] += 1
        return data.copy()

    cached_aggregation(aggregate, frame, ttl_seconds=0)
    time.sleep(0.001)
    cached_aggregation(aggregate, frame, ttl_seconds=0)

    assert calls["count"] == 2


def test_cached_aggregation_supports_scalar_values() -> None:
    clear_memory_cache()
    frame = pd.DataFrame({"valor": [1, 2, 3]})

    def aggregate(data: pd.DataFrame) -> int:
        return int(data["valor"].sum())

    assert cached_aggregation(aggregate, frame) == 6


def test_path_fingerprint_tracks_missing_and_file_changes(tmp_path) -> None:
    missing = tmp_path / "missing.csv"
    assert path_fingerprint(missing) == "missing"

    path = tmp_path / "data.csv"
    path.write_text("a\n1\n", encoding="utf-8")
    first = path_fingerprint(path)
    path.write_text("a\n2\n", encoding="utf-8")

    assert first != path_fingerprint(path)


def test_load_or_build_disk_cache_reuses_pickle(tmp_path) -> None:
    calls = {"count": 0}

    def builder() -> dict[str, int]:
        calls["count"] += 1
        return {"value": 10}

    first = load_or_build_disk_cache(tmp_path, "executive", "abc", builder)
    second = load_or_build_disk_cache(tmp_path, "executive", "abc", builder)

    assert first == {"value": 10}
    assert second == first
    assert calls["count"] == 1
    assert disk_cache_path(tmp_path, "executive", "abc").exists()
    assert disk_cache_path(tmp_path, "exec utive/ce", "abc").name == "exec_utive_ce_abc.pkl"
