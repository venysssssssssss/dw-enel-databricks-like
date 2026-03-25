"""Optional Great Expectations runner backed by declarative suite definitions."""

from __future__ import annotations

from src.quality.contracts import CheckpointDefinition


class GreatExpectationsRunner:
    def __init__(self) -> None:
        try:
            import great_expectations as gx
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Great Expectations não está instalado. Use `pip install -e \".[platform]\"`."
            ) from exc
        self._gx = gx

    def run_checkpoint(self, checkpoint: CheckpointDefinition) -> dict[str, int]:
        return {
            "checkpoint_name": checkpoint.name,
            "validation_count": len(checkpoint.validations),
        }
