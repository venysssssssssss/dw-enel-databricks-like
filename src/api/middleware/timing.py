"""Response timing middleware."""

from __future__ import annotations

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started_at = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started_at
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        return response
