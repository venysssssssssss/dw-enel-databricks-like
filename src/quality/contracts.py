"""Declarative quality contracts used to build Great Expectations assets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ExpectationDefinition:
    expectation_type: str
    kwargs: dict[str, Any]
    critical: bool = False


@dataclass(frozen=True, slots=True)
class ValidationSuite:
    name: str
    table_name: str
    expectations: tuple[ExpectationDefinition, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CheckpointDefinition:
    name: str
    validations: tuple[ValidationSuite, ...]
