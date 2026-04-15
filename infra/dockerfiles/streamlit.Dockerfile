# Streamlit image with dashboard deps pre-baked so container restarts are instant.
# Build context: project root.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install build deps for any wheels that need compilation (e.g. hdbscan).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache).
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip \
    && pip install -e ".[viz,rag]"

# App code is mounted at runtime via docker-compose (volume), but we copy as
# fallback so the image is self-contained.
COPY apps/ ./apps/

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
