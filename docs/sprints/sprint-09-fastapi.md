# Sprint 09 — FastAPI: Exportação e Consulta

**Fase**: 3 — Gold & Consumo
**Duração**: 2 semanas
**Objetivo**: Implementar a API FastAPI completa para exportação filtrada de dados, consulta de métricas e scores, com autenticação JWT, streaming e documentação OpenAPI.

**Pré-requisito**: Sprint 07 completa (Gold layer disponível)

---

## Backlog da Sprint

### US-045: FastAPI — App Factory e Infraestrutura
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/api/main.py`**:
   ```python
   from contextlib import asynccontextmanager
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware

   from src.api.config import settings
   from src.api.middleware.request_id import RequestIDMiddleware
   from src.api.middleware.timing import TimingMiddleware
   from src.api.routers.v1 import exports, scores, metrics, health

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup: inicializar conexões
       app.state.trino_pool = await create_trino_pool()
       app.state.minio = create_minio_client()
       yield
       # Shutdown: limpar recursos
       await app.state.trino_pool.close()

   def create_app() -> FastAPI:
       app = FastAPI(
           title="ENEL Analytics Platform API",
           description="API para exportação de dados operacionais e scores preditivos",
           version="1.0.0",
           lifespan=lifespan,
           docs_url="/api/docs",
           redoc_url="/api/redoc",
           openapi_url="/api/openapi.json",
       )

       # Middleware (ordem importa: último adicionado = primeiro executado)
       app.add_middleware(TimingMiddleware)
       app.add_middleware(RequestIDMiddleware)
       app.add_middleware(
           CORSMiddleware,
           allow_origins=settings.cors_origins,
           allow_methods=["*"],
           allow_headers=["*"],
       )

       # Routers
       app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
       app.include_router(exports.router, prefix="/api/v1/exports", tags=["Exports"])
       app.include_router(scores.router, prefix="/api/v1/scores", tags=["Scores"])
       app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"])

       return app

   app = create_app()
   ```

2. **Criar `src/api/config.py`** (conforme `docs/api/01-fastapi-design.md`)

3. **Criar middleware**:

   `src/api/middleware/request_id.py`:
   ```python
   class RequestIDMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           request_id = request.headers.get("X-Request-ID", str(uuid4()))
           structlog.contextvars.bind_contextvars(request_id=request_id)
           response = await call_next(request)
           response.headers["X-Request-ID"] = request_id
           return response
   ```

   `src/api/middleware/timing.py`:
   ```python
   class TimingMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           start = time.perf_counter()
           response = await call_next(request)
           duration = time.perf_counter() - start
           response.headers["X-Response-Time"] = f"{duration:.3f}s"
           return response
   ```

4. **Criar Dockerfile** (`infra/dockerfiles/Dockerfile.api`):
   ```dockerfile
   FROM python:3.12-slim

   WORKDIR /app
   COPY pyproject.toml .
   RUN pip install --no-cache-dir ".[api]"

   COPY src/ ./src/
   EXPOSE 8000
   CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
   ```

5. **Adicionar ao Docker Compose**:
   ```yaml
   api:
     build:
       context: ..
       dockerfile: infra/dockerfiles/Dockerfile.api
     ports:
       - "8000:8000"
     environment:
       ENEL_TRINO_HOST: trino
       ENEL_MINIO_ENDPOINT: minio:9000
       ENEL_SECRET_KEY: ${ENEL_SECRET_KEY}
     depends_on:
       trino:
         condition: service_started
       minio:
         condition: service_healthy
     deploy:
       resources:
         limits:
           memory: 256M
   ```

**Critério de aceite**:
- API acessível em `http://localhost:8000`
- OpenAPI docs em `http://localhost:8000/api/docs`
- Health check retorna status dos serviços
- Middleware de request ID e timing funcionais

---

### US-046: Trino Async Client
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/api/infrastructure/trino_client.py`**:
   ```python
   """Cliente Trino assíncrono para FastAPI."""
   import httpx
   from typing import AsyncIterator

   class AsyncTrinoClient:
       """Executa queries no Trino de forma assíncrona."""

       def __init__(self, host: str, port: int, catalog: str, schema: str):
           self.base_url = f"http://{host}:{port}"
           self.catalog = catalog
           self.schema = schema
           self._client = httpx.AsyncClient(timeout=60.0)

       async def execute(self, query: str) -> list[dict]:
           """Executa query e retorna todos os resultados."""
           rows = []
           async for batch in self.execute_streaming(query):
               rows.extend(batch)
           return rows

       async def execute_streaming(
           self, query: str, batch_size: int = 5000
       ) -> AsyncIterator[list[dict]]:
           """Executa query e retorna resultados em batches (streaming)."""
           # Submit query
           response = await self._client.post(
               f"{self.base_url}/v1/statement",
               content=query,
               headers={
                   "X-Trino-User": "enel",
                   "X-Trino-Catalog": self.catalog,
                   "X-Trino-Schema": self.schema,
               },
           )
           result = response.json()
           columns = [c["name"] for c in result.get("columns", [])]

           # Fetch results
           while True:
               if "data" in result:
                   rows = [dict(zip(columns, row)) for row in result["data"]]
                   # Yield in batches
                   for i in range(0, len(rows), batch_size):
                       yield rows[i:i + batch_size]

               next_uri = result.get("nextUri")
               if not next_uri:
                   break
               response = await self._client.get(next_uri)
               result = response.json()

       async def close(self):
           await self._client.aclose()
   ```

**Critério de aceite**:
- Queries executam de forma assíncrona
- Streaming funciona para resultados grandes
- Timeout configurável
- Cleanup de conexões no shutdown

---

### US-047: Endpoints de Exportação
**Prioridade**: P0
**Story Points**: 8

**Tarefas**:

1. **Criar schemas** (`src/api/schemas/exports.py`) conforme `docs/api/01-fastapi-design.md`

2. **Criar `src/api/services/export_service.py`**:
   ```python
   class ExportService:
       """Serviço de exportação de dados filtrados."""

       def __init__(self, trino: AsyncTrinoClient, minio: MinIOClient):
           self.trino = trino
           self.minio = minio

       async def export_notas(
           self, filters: ExportNotasRequest, format: ExportFormat
       ) -> ExportResponse:
           query = self._build_query("fato_notas_operacionais", filters)
           results = await self.trino.execute(query)
           file_path = self._write_file(results, format)
           url = self.minio.get_presigned_url("exports", file_path)
           return ExportResponse(
               export_id=str(uuid4()),
               status="READY",
               download_url=url,
               row_count=len(results),
               format=format,
           )

       def _build_query(self, table: str, filters) -> str:
           """Constrói query SQL com filtros dinâmicos (parameterized)."""
           conditions = []
           if filters.distribuidora:
               conditions.append(f"dd.cod_distribuidora = {int(filters.distribuidora)}")
           if filters.ut:
               conditions.append(f"du.cod_ut = {int(filters.ut)}")
           if filters.co:
               conditions.append(f"dc.cod_co = {int(filters.co)}")
           if filters.base:
               conditions.append(f"db.cod_base = {int(filters.base)}")
           conditions.append(
               f"dt.data BETWEEN DATE '{filters.periodo_inicio}' AND DATE '{filters.periodo_fim}'"
           )
           if filters.classificacao_acf_asf:
               vals = ", ".join(f"'{v}'" for v in filters.classificacao_acf_asf)
               conditions.append(f"f.classificacao_acf_asf IN ({vals})")

           where_clause = " AND ".join(conditions)
           return f"""
               SELECT f.*, dt.data, dt.ano_mes,
                      dd.nome_distribuidora, du.nome_ut, dc.nome_co, db.nome_base
               FROM gold.fato_notas_operacionais f
               JOIN gold.dim_tempo dt ON f.sk_tempo = dt.sk_tempo
               JOIN gold.dim_distribuidora dd ON f.sk_distribuidora = dd.sk_distribuidora
               JOIN gold.dim_ut du ON f.sk_ut = du.sk_ut
               JOIN gold.dim_co dc ON f.sk_co = dc.sk_co
               JOIN gold.dim_base db ON f.sk_base = db.sk_base
               WHERE {where_clause}
               ORDER BY dt.data DESC
           """
   ```

3. **Criar `src/api/routers/v1/exports.py`**:
   ```python
   router = APIRouter()

   @router.post("/notas", response_model=ExportResponse)
   async def export_notas(
       filters: ExportNotasRequest,
       format: ExportFormat = Query(default=ExportFormat.CSV),
       current_user: Annotated[User, Depends(get_current_user)],
       export_service: Annotated[ExportService, Depends(get_export_service)],
   ) -> ExportResponse:
       return await export_service.export_notas(filters, format)

   @router.get("/notas/stream")
   async def stream_notas(
       filters: Annotated[ExportNotasFilters, Depends()],
       export_service: Annotated[ExportService, Depends(get_export_service)],
   ) -> StreamingResponse:
       return await export_service.stream_notas(filters)
   ```

4. **Implementar exports para todos os domínios**:
   - `/api/v1/exports/notas`
   - `/api/v1/exports/entregas`
   - `/api/v1/exports/pagamentos`
   - `/api/v1/exports/metas`
   - `/api/v1/exports/efetividade`

5. **Implementar streaming** para datasets > 10k registros

**Critério de aceite**:
- Cada endpoint retorna dados filtrados corretamente
- Export CSV/Parquet/JSON funcional
- Streaming funciona sem OOM para 100k+ registros
- Filtros de hierarquia (distribuidora→UT→CO→base) validados
- OpenAPI docs mostra todos os parâmetros

---

### US-048: Autenticação JWT
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Criar `src/api/auth/jwt.py`**:
   ```python
   from datetime import datetime, timedelta
   from jose import JWTError, jwt
   from passlib.context import CryptContext

   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
       to_encode = data.copy()
       expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
       to_encode.update({"exp": expire})
       return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

   async def get_current_user(
       token: Annotated[str, Depends(oauth2_scheme)]
   ) -> User:
       try:
           payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
           user_id: str = payload.get("sub")
           if user_id is None:
               raise HTTPException(status_code=401, detail="Invalid token")
           return await get_user(user_id)
       except JWTError:
           raise HTTPException(status_code=401, detail="Invalid token")
   ```

2. **Criar endpoint de login**:
   ```python
   @router.post("/token", response_model=TokenResponse)
   async def login(form: OAuth2PasswordRequestForm = Depends()):
       user = authenticate_user(form.username, form.password)
       if not user:
           raise HTTPException(status_code=401, detail="Invalid credentials")
       token = create_access_token(data={"sub": user.id, "role": user.role})
       return TokenResponse(access_token=token, token_type="bearer")
   ```

3. **Criar sistema de permissões por role**:
   ```python
   class Role(str, Enum):
       ADMIN = "admin"
       ANALYST = "analyst"
       VIEWER = "viewer"

   def require_role(allowed_roles: list[Role]):
       async def role_checker(user: User = Depends(get_current_user)):
           if user.role not in allowed_roles:
               raise HTTPException(status_code=403, detail="Insufficient permissions")
           return user
       return role_checker
   ```

**Critério de aceite**:
- Login retorna JWT válido
- Endpoints protegidos rejeitam requests sem token
- Roles admin/analyst/viewer com permissões diferentes
- Token expira conforme configurado

---

### US-049: Rate Limiting e Error Handling
**Prioridade**: P1
**Story Points**: 3

**Tarefas**:

1. **Rate limiting** com slowapi:
   ```python
   limiter = Limiter(key_func=get_remote_address)
   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

   # Limites por endpoint
   @router.get("/notas/stream")
   @limiter.limit("10/minute")
   async def stream_notas(...): ...

   @router.post("/notas")
   @limiter.limit("30/minute")
   async def export_notas(...): ...
   ```

2. **Error handling centralizado** (`src/api/exceptions.py`):
   ```python
   @app.exception_handler(TrinoError)
   async def trino_error_handler(request: Request, exc: TrinoError):
       logger.error("trino_error", error=str(exc), request_id=request.state.request_id)
       return JSONResponse(status_code=502, content={"detail": "Database query failed"})

   @app.exception_handler(ValidationError)
   async def validation_error_handler(request: Request, exc: ValidationError):
       return JSONResponse(status_code=422, content={"detail": exc.errors()})
   ```

**Critério de aceite**:
- Rate limit retorna 429 quando excedido
- Erros de Trino retornam 502 (não 500)
- Erros de validação retornam 422 com detalhes
- Todos os erros logados com request_id

---

### US-050: Testes da API
**Prioridade**: P0
**Story Points**: 5

**Tarefas**:

1. **Testes unitários** (`tests/unit/test_api/`):
   ```python
   from httpx import AsyncClient, ASGITransport
   import pytest

   @pytest.fixture
   async def client():
       async with AsyncClient(
           transport=ASGITransport(app=app), base_url="http://test"
       ) as ac:
           yield ac

   async def test_health_check(client):
       response = await client.get("/api/v1/health/")
       assert response.status_code == 200

   async def test_export_notas_requires_auth(client):
       response = await client.post("/api/v1/exports/notas", json={...})
       assert response.status_code == 401

   async def test_export_notas_with_filters(authenticated_client):
       response = await authenticated_client.post(
           "/api/v1/exports/notas",
           json={
               "distribuidora": 1,
               "periodo_inicio": "2026-01-01",
               "periodo_fim": "2026-03-31",
           }
       )
       assert response.status_code == 200
       data = response.json()
       assert data["status"] == "READY"
       assert data["row_count"] > 0
   ```

2. **Testes de integração** — contra Trino real

**Critério de aceite**:
- Cobertura ≥ 80% nos routers e services
- Todos os endpoints testados (happy path + erros)
- Testes de auth (com e sem token)
- Testes de rate limiting

---

## Entregáveis da Sprint

| Entregável | Status |
|---|---|
| FastAPI app com lifespan, middleware e routers | |
| Trino async client com streaming | |
| 5 endpoints de exportação (notas, entregas, pagamentos, metas, efetividade) | |
| Streaming response para exports grandes | |
| Autenticação JWT com roles | |
| Rate limiting | |
| Error handling centralizado | |
| Testes unitários e integração (≥80% coverage) | |
| OpenAPI docs auto-gerados | |
| Dockerfile + Docker Compose | |
