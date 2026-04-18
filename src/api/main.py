"""FastAPI app factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.api.config import get_api_settings
from src.api.exceptions import (
    TrinoError,
    request_validation_error_handler,
    trino_error_handler,
    validation_error_handler,
)
from src.api.infrastructure.trino_client import AsyncTrinoClient
from src.api.middleware.request_id import RequestIDMiddleware
from src.api.middleware.timing import TimingMiddleware
from src.api.routers import dashboard, rag
from src.api.routers.v1 import admin, erro_leitura, exports, health, metrics, scores
from src.common.minio_client import MinIOClient
from src.rag.config import load_rag_config
from src.rag.orchestrator import RagOrchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_api_settings()
    app.state.trino = AsyncTrinoClient(
        host=settings.trino_host,
        port=settings.trino_port,
        catalog=settings.trino_catalog,
        schema=settings.trino_schema,
    )
    app.state.minio = MinIOClient(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
    )
    # Warm singleton do RAG para reduzir overhead de cold-start por request SSE.
    try:
        rag_config = load_rag_config()
        app.state.rag_config = rag_config
        app.state.rag_orchestrator = RagOrchestrator(rag_config)
    except Exception:
        # Nunca quebrar boot da API por falha de inicialização do RAG.
        app.state.rag_orchestrator = None
    yield
    await app.state.trino.close()


def create_app(
    *,
    enable_lifespan: bool = True,
    enable_rate_limit: bool = True,
    enable_observability: bool = True,
    enable_middlewares: bool = True,
) -> FastAPI:
    settings = get_api_settings()
    app = FastAPI(
        title=settings.app_name,
        description="API para exportação, métricas e scores preditivos",
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan if enable_lifespan else None,
    )
    app.state.limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.rate_limit_default],
    )
    app.add_exception_handler(TrinoError, trino_error_handler)
    app.add_exception_handler(ValueError, validation_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    if enable_rate_limit:
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
    if enable_middlewares:
        app.add_middleware(TimingMiddleware)
        app.add_middleware(RequestIDMiddleware)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
    app.include_router(exports.router, prefix="/api/v1/exports", tags=["Exports"])
    app.include_router(scores.router, prefix="/api/v1/scores", tags=["Scores"])
    app.include_router(
        erro_leitura.router,
        prefix="/api/v1/erros-leitura",
        tags=["Erros de Leitura"],
    )
    app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(dashboard.router, prefix="/v1", tags=["Unified Data Plane"])
    app.include_router(rag.router, prefix="/v1", tags=["RAG"])

    if enable_observability:
        Instrumentator().instrument(app).expose(app)
    return app


app = create_app()
