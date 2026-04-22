FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal --default-toolchain 1.86.0

ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app
COPY rust/ /app/rust/
RUN python -m pip install --no-cache-dir "maturin>=1.7,<2.0"

WORKDIR /app/rust/enel_core
CMD ["maturin", "build", "--release"]
