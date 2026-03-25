"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
from typing import Any

import structlog

from src.common.config import get_settings


def setup_logging(level: str | None = None, json_output: bool | None = None) -> None:
    settings = get_settings()
    resolved_level = getattr(logging, (level or settings.log_level).upper(), logging.INFO)
    resolved_json_output = settings.log_json if json_output is None else json_output

    logging.basicConfig(
        format="%(message)s",
        level=resolved_level,
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
    ]

    if resolved_json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(resolved_level),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def bind_pipeline_context(**context: Any) -> None:
    structlog.contextvars.bind_contextvars(**context)


def clear_pipeline_context() -> None:
    structlog.contextvars.clear_contextvars()


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
