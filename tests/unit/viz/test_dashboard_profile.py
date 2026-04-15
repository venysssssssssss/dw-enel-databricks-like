from __future__ import annotations

from scripts.profile_dashboard_cache import _p95


def test_p95_handles_empty_single_and_multiple_values() -> None:
    assert _p95([]) == 0.0
    assert _p95([12.0]) == 12.0
    assert _p95(list(range(1, 21))) == 19.95
