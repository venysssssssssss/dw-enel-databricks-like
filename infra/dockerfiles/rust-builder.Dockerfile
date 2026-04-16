FROM rust:1.82-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY rust/ /app/rust/
RUN python3 -m pip install --break-system-packages maturin==1.7.8

WORKDIR /app/rust/enel_core
CMD ["maturin", "build", "--release"]
