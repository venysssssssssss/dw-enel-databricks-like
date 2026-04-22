# Streamlit image with dashboard deps, Rust hot paths and embedded React assets.
# Build context: project root.
FROM python:3.12-slim AS enel-core-wheel

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal --default-toolchain 1.86.0

ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /build
COPY rust/ ./rust/
RUN python -m pip install --no-cache-dir "maturin>=1.7,<2.0" \
    && cd rust/enel_core \
    && maturin build --release -o /wheels

FROM node:24-alpine AS streamlit-react-assets

WORKDIR /build/apps/web
COPY apps/web/package.json apps/web/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY apps/web/ ./
RUN pnpm build:streamlit

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install build deps for any wheels that need compilation (e.g. hdbscan,
# llama-cpp-python which builds a native CMake extension).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential curl cmake git \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache).
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY --from=enel-core-wheel /wheels/*.whl /tmp/

RUN pip install --upgrade pip \
    && pip install -e ".[viz,rag]" \
    && pip install /tmp/enel_core-*.whl \
    && rm -f /tmp/enel_core-*.whl

# App code is mounted at runtime via docker-compose (volume), but we copy as
# fallback so the image is self-contained.
COPY apps/ ./apps/
COPY --from=streamlit-react-assets /build/apps/streamlit/static/ ./apps/streamlit/static/

EXPOSE 8501

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "apps/streamlit/erro_leitura_dashboard.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false", \
     "--browser.gatherUsageStats=false"]
