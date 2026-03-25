"""Small serialization helpers used by audit pipelines."""

from __future__ import annotations

import json
from typing import Any


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
