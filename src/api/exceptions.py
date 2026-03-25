"""API exceptions and handlers."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.common.logging import get_logger

logger = get_logger(__name__)


class TrinoError(RuntimeError):
    """Raised when a Trino query fails."""


async def trino_error_handler(request: Request, exc: TrinoError) -> JSONResponse:
    logger.error("trino_error", error=str(exc), path=str(request.url))
    return JSONResponse(status_code=502, content={"detail": "Database query failed"})


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger.warning("validation_error", path=str(request.url), errors=exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    logger.warning("request_validation_error", path=str(request.url), errors=exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
