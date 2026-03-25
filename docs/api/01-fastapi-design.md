# FastAPI — Design da Camada de API

## Versão e Features Utilizados

**FastAPI 0.115+** com Pydantic v2, aproveitando as melhores features disponíveis:

| Feature | Uso no Projeto |
|---|---|
| **Pydantic v2** | Validação de input/output 5-50x mais rápida (core em Rust) |
| **Lifespan Events** | Inicializar conexão Trino e MLflow no startup, cleanup no shutdown |
| **Dependency Injection** | Auth, database sessions, rate limiting, logging |
| **Streaming Responses** | Export de datasets grandes sem carregar tudo em memória |
| **Background Tasks** | Gerar exports assíncronos e notificar quando prontos |
| **OpenAPI 3.1** | Documentação auto-gerada para equipe de operação |
| **Annotated Dependencies** | Type-safe DI com `Annotated[T, Depends()]` |
| **Model Serialization** | `model_config` com `from_attributes=True` para ORM |
| **Exception Handlers** | Tratamento centralizado de erros com structured logging |
| **Middleware** | CORS, request ID tracking, response timing |
| **Router Prefixes** | Modularização por domínio (v1/exports, v1/scores, v1/health) |

---

## Arquitetura da API

```
┌──────────────────────────────────────────────────────────┐
│                     FastAPI App                           │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │  Auth       │  │  Rate      │  │  Request ID        │ │
│  │  Middleware  │  │  Limiter   │  │  Middleware         │ │
│  └──────┬─────┘  └──────┬─────┘  └──────────┬─────────┘ │
│         └───────────────┴──────────────┬─────┘           │
│                                        │                  │
│  ┌─────────────────────────────────────┴───────────────┐ │
│  │                   Router Layer                       │ │
│  │                                                     │ │
│  │  /api/v1/exports/    → ExportRouter                 │ │
│  │  /api/v1/scores/     → ScoresRouter                 │ │
│  │  /api/v1/metrics/    → MetricsRouter                │ │
│  │  /api/v1/health/     → HealthRouter                 │ │
│  │  /api/v1/admin/      → AdminRouter                  │ │
│  └─────────────────────────────────────────────────────┘ │
│                         │                                 │
│  ┌──────────────────────┴──────────────────────────────┐ │
│  │                  Service Layer                       │ │
│  │                                                     │ │
│  │  ExportService   → Queries Trino, gera exports      │ │
│  │  ScoreService    → Lê scores do MinIO/Gold          │ │
│  │  MetricsService  → Agrega métricas operacionais     │ │
│  └─────────────────────────────────────────────────────┘ │
│                         │                                 │
│  ┌──────────────────────┴──────────────────────────────┐ │
│  │              Infrastructure Layer                    │ │
│  │                                                     │ │
│  │  TrinoClient (async)  │  MinIOClient  │  MLflowClient│ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## Estrutura de Diretórios

```
src/api/
├── main.py                    # App factory, lifespan, middleware
├── config.py                  # Settings via pydantic-settings
├── dependencies.py            # Shared dependencies (auth, db, rate limit)
├── exceptions.py              # Custom exception handlers
├── middleware/
│   ├── __init__.py
│   ├── request_id.py          # X-Request-ID tracking
│   ├── timing.py              # Response time header
│   └── cors.py                # CORS config
├── routers/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── exports.py         # /api/v1/exports/
│   │   ├── scores.py          # /api/v1/scores/
│   │   ├── metrics.py         # /api/v1/metrics/
│   │   ├── health.py          # /api/v1/health/
│   │   └── admin.py           # /api/v1/admin/
├── schemas/
│   ├── __init__.py
│   ├── common.py              # Pagination, filters, responses
│   ├── exports.py             # Export request/response models
│   ├── scores.py              # Score response models
│   └── metrics.py             # Metrics response models
├── services/
│   ├── __init__.py
│   ├── export_service.py
│   ├── score_service.py
│   └── metrics_service.py
├── infrastructure/
│   ├── __init__.py
│   ├── trino_client.py        # Async Trino connection
│   ├── minio_client.py        # MinIO S3 client
│   └── mlflow_client.py       # MLflow model loading
└── auth/
    ├── __init__.py
    ├── jwt.py                 # JWT token creation/validation
    └── permissions.py         # Role-based access control
```

## Endpoints Detalhados

### Exports — Exportação Filtrada de Dados

```python
# POST /api/v1/exports/notas
# Exporta notas operacionais com filtros
@router.post("/notas", response_model=ExportResponse)
async def export_notas(
    filters: ExportNotasRequest,
    format: ExportFormat = Query(default=ExportFormat.CSV),
    current_user: Annotated[User, Depends(get_current_user)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportResponse:
    ...

# GET /api/v1/exports/notas/stream
# Streaming export para datasets grandes (>100k registros)
@router.get("/notas/stream")
async def stream_notas(
    filters: Annotated[ExportNotasFilters, Depends()],
    format: ExportFormat = Query(default=ExportFormat.CSV),
    current_user: Annotated[User, Depends(get_current_user)],
    export_service: Annotated[ExportService, Depends(get_export_service)],
) -> StreamingResponse:
    ...

# POST /api/v1/exports/entregas
@router.post("/entregas", response_model=ExportResponse)
async def export_entregas(...): ...

# POST /api/v1/exports/pagamentos
@router.post("/pagamentos", response_model=ExportResponse)
async def export_pagamentos(...): ...

# POST /api/v1/exports/metas
@router.post("/metas", response_model=ExportResponse)
async def export_metas(...): ...

# POST /api/v1/exports/efetividade
@router.post("/efetividade", response_model=ExportResponse)
async def export_efetividade(...): ...
```

### Scores — Consulta de Scores Preditivos

```python
# GET /api/v1/scores/atraso
# Consulta scores de atraso com filtros
@router.get("/atraso", response_model=PaginatedResponse[ScoreAtrasoResponse])
async def get_scores_atraso(
    distribuidora: int | None = None,
    ut: int | None = None,
    co: int | None = None,
    base: int | None = None,
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    data_scoring: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    current_user: Annotated[User, Depends(get_current_user)],
    score_service: Annotated[ScoreService, Depends(get_score_service)],
) -> PaginatedResponse[ScoreAtrasoResponse]:
    ...

# GET /api/v1/scores/atraso/{cod_nota}
# Score individual com explicabilidade
@router.get("/atraso/{cod_nota}", response_model=ScoreAtrasoDetailResponse)
async def get_score_atraso_detail(
    cod_nota: int,
    current_user: Annotated[User, Depends(get_current_user)],
    score_service: Annotated[ScoreService, Depends(get_score_service)],
) -> ScoreAtrasoDetailResponse:
    ...

# GET /api/v1/scores/inadimplencia
@router.get("/inadimplencia", response_model=PaginatedResponse[ScoreInadimplenciaResponse])
async def get_scores_inadimplencia(...): ...

# GET /api/v1/scores/metas
@router.get("/metas", response_model=PaginatedResponse[ScoreMetaResponse])
async def get_scores_metas(...): ...

# GET /api/v1/scores/anomalias
@router.get("/anomalias", response_model=PaginatedResponse[AnomaliaResponse])
async def get_anomalias(...): ...
```

### Metrics — Métricas Operacionais Agregadas

```python
# GET /api/v1/metrics/efetividade
@router.get("/efetividade", response_model=EfetividadeResponse)
async def get_efetividade(
    distribuidora: int,
    periodo_inicio: date,
    periodo_fim: date,
    granularidade: Granularidade = Query(default=Granularidade.CO),
    ut: int | None = None,
    co: int | None = None,
    ...
) -> EfetividadeResponse:
    ...

# GET /api/v1/metrics/atraso/summary
@router.get("/atraso/summary", response_model=AtrasoSummaryResponse)
async def get_atraso_summary(...): ...

# GET /api/v1/metrics/metas/projecao
@router.get("/metas/projecao", response_model=ProjecaoMetaResponse)
async def get_projecao_meta(...): ...
```

### Health & Admin

```python
# GET /api/v1/health/
@router.get("/", response_model=HealthResponse)
async def health_check(
    trino: Annotated[TrinoClient, Depends(get_trino)],
    minio: Annotated[MinIOClient, Depends(get_minio)],
) -> HealthResponse:
    ...

# GET /api/v1/health/ready
@router.get("/ready")
async def readiness(): ...

# GET /api/v1/admin/pipeline/status
@router.get("/pipeline/status", response_model=PipelineStatusResponse)
async def pipeline_status(...): ...
```

## Schemas Pydantic v2

### Filtros Comuns

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import date
from enum import Enum

class ExportFormat(str, Enum):
    CSV = "csv"
    PARQUET = "parquet"
    EXCEL = "xlsx"
    JSON = "json"

class Granularidade(str, Enum):
    DISTRIBUIDORA = "distribuidora"
    UT = "ut"
    CO = "co"
    BASE = "base"
    LOTE = "lote"
    COLABORADOR = "colaborador"

class OperationalFilters(BaseModel):
    """Filtros operacionais reutilizáveis."""
    model_config = ConfigDict(str_strip_whitespace=True)

    distribuidora: int | None = Field(None, description="Código da distribuidora")
    ut: int | None = Field(None, description="Código da UT")
    co: int | None = Field(None, description="Código do CO")
    base: int | None = Field(None, description="Código da base/polo")
    lote: int | None = Field(None, description="Código do lote")
    periodo_inicio: date = Field(..., description="Data início do período")
    periodo_fim: date = Field(..., description="Data fim do período")

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)

class PaginatedResponse[T](BaseModel):
    """Response paginada genérica — usa Python 3.12 generic syntax."""
    data: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

### Export Schemas

```python
class ExportNotasRequest(OperationalFilters):
    """Request para exportação de notas operacionais."""
    classificacao_acf_asf: list[str] | None = Field(
        None,
        description="Filtro por classificação ACF/ASF"
    )
    status: list[str] | None = Field(None, description="Status da nota")
    flag_risco: bool | None = Field(None, description="Filtrar por risco")
    tipo_servico: list[str] | None = None

class ExportResponse(BaseModel):
    """Response com link para download ou status de processamento."""
    model_config = ConfigDict(from_attributes=True)

    export_id: str = Field(..., description="ID único do export")
    status: str = Field(..., description="READY | PROCESSING | FAILED")
    download_url: str | None = Field(None, description="URL para download (quando READY)")
    row_count: int | None = Field(None, description="Total de registros")
    file_size_bytes: int | None = None
    format: ExportFormat
    created_at: datetime
    expires_at: datetime | None = None
```

### Score Schemas

```python
class ScoreAtrasoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cod_nota: int
    cod_uc: int
    distribuidora: str
    ut: str
    co: str
    base: str
    score_atraso: float = Field(..., ge=0.0, le=1.0)
    classe_predita: str
    dias_atraso_estimado: float | None
    confianca: float
    data_scoring: date

class ScoreAtrasoDetailResponse(ScoreAtrasoResponse):
    """Score com explicabilidade SHAP."""
    explicacao: list[FeatureContribution]
    model_version: str

class FeatureContribution(BaseModel):
    feature_name: str
    feature_value: float | str
    shap_value: float
    direction: str = Field(..., description="AUMENTA_RISCO | DIMINUI_RISCO")
```

## Lifespan Events (Startup/Shutdown)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.trino_pool = await create_trino_pool(settings.trino_url)
    app.state.minio_client = create_minio_client(settings.minio_url)
    app.state.mlflow_client = create_mlflow_client(settings.mlflow_url)

    yield

    # Shutdown
    await app.state.trino_pool.close()

app = FastAPI(
    title="ENEL Analytics Platform API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
```

## Streaming para Exports Grandes

```python
from fastapi.responses import StreamingResponse
import csv
import io

async def stream_csv_export(query: str, trino: TrinoClient):
    """Gera CSV em chunks via streaming — não carrega tudo em memória."""

    async def generate():
        header_sent = False
        async for batch in trino.execute_streaming(query, batch_size=5000):
            output = io.StringIO()
            writer = csv.writer(output, delimiter=';')

            if not header_sent:
                writer.writerow(batch.columns)
                header_sent = True

            for row in batch.rows:
                writer.writerow(row)

            yield output.getvalue()
            output.close()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=export.csv",
            "X-Stream": "true",
        },
    )
```

## Autenticação JWT

```python
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return await get_user(user_id)
    except JWTError:
        raise credentials_exception
```

## Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/notas/stream")
@limiter.limit("10/minute")
async def stream_notas(request: Request, ...):
    ...
```

## Configuração via Pydantic Settings

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ENEL_",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 2
    debug: bool = False

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 30

    # Trino
    trino_host: str = "localhost"
    trino_port: int = 8443
    trino_catalog: str = "iceberg"
    trino_schema: str = "gold"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "lakehouse"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Rate Limiting
    rate_limit_per_minute: int = 60

settings = Settings()
```
