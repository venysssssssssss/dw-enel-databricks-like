from __future__ import annotations

from src.quality.suites import build_default_checkpoints


def test_default_checkpoints_have_bronze_and_silver() -> None:
    checkpoints = {checkpoint.name: checkpoint for checkpoint in build_default_checkpoints()}
    assert "checkpoint_bronze_daily" in checkpoints
    assert "checkpoint_silver_daily" in checkpoints
    assert len(checkpoints["checkpoint_bronze_daily"].validations) >= 3
