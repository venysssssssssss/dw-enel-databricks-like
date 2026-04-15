"""Configuração do chat RAG, carregada de variáveis de ambiente.

Default 100% open-source, CPU-only: llama-cpp-python + ChromaDB + MiniLM PT-BR.
Não exige chave de API; o modelo GGUF é baixado sob demanda do Hugging Face.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_LLAMA_REPO = "Qwen/Qwen2.5-3B-Instruct-GGUF"
_DEFAULT_LLAMA_FILE = "qwen2.5-3b-instruct-q4_k_m.gguf"
_DEFAULT_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


@dataclass(frozen=True, slots=True)
class RagConfig:
    """Configurações do chat RAG.

    Valores default são escolhidos para rodar em notebook 16GB RAM, CPU-only:
    Qwen2.5-3B-Instruct quantizado Q4_K_M (~2GB de RAM) + MiniLM PT-BR (~120MB).
    """

    provider: str  # "llama_cpp" | "openai" | "anthropic" | "ollama" | "stub"
    model_repo: str
    model_file: str
    model_path: Path | None
    embedding_model: str
    chromadb_path: Path
    collection_name: str
    max_turn_tokens: int
    max_context_tokens: int
    rerank_enabled: bool
    stream: bool
    retrieval_k: int
    rerank_top_n: int
    similarity_threshold: float
    corpus_roots: tuple[Path, ...]
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    n_threads: int
    n_ctx: int
    temperature: float
    top_p: float
    api_key: str | None
    telemetry_path: Path
    feedback_path: Path


def _env_path(key: str, default: str) -> Path:
    return Path(os.getenv(key, default)).expanduser()


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_rag_config() -> RagConfig:
    """Lê variáveis de ambiente e retorna `RagConfig`.

    Nunca lança: se algo estiver faltando, aplica default seguro.
    """

    project_root = Path(os.getenv("ENEL_PROJECT_ROOT", ".")).resolve()
    corpus_roots = tuple(
        (project_root / rel).resolve()
        for rel in ("docs", "README.md", "CLAUDE.md")
        if (project_root / rel).exists()
    )

    model_path_raw = os.getenv("RAG_MODEL_PATH")
    model_path = Path(model_path_raw).expanduser() if model_path_raw else None

    return RagConfig(
        provider=os.getenv("RAG_PROVIDER", "llama_cpp").lower(),
        model_repo=os.getenv("RAG_MODEL_REPO", _DEFAULT_LLAMA_REPO),
        model_file=os.getenv("RAG_MODEL_FILE", _DEFAULT_LLAMA_FILE),
        model_path=model_path,
        embedding_model=os.getenv("RAG_EMBEDDING_MODEL", _DEFAULT_EMBED_MODEL),
        chromadb_path=_env_path("RAG_CHROMADB_PATH", "data/rag/chromadb"),
        collection_name=os.getenv("RAG_COLLECTION", "enel_docs"),
        max_turn_tokens=_env_int("RAG_MAX_TURN_TOKENS", 3000),
        max_context_tokens=_env_int("RAG_MAX_CONTEXT_TOKENS", 4096),
        rerank_enabled=_env_bool("RAG_RERANK_ENABLED", False),
        stream=_env_bool("RAG_STREAM", True),
        retrieval_k=_env_int("RAG_RETRIEVAL_K", 12),
        rerank_top_n=_env_int("RAG_RERANK_TOP_N", 5),
        similarity_threshold=_env_float("RAG_SIMILARITY_THRESHOLD", 0.25),
        corpus_roots=corpus_roots,
        chunk_size_tokens=_env_int("RAG_CHUNK_SIZE", 480),
        chunk_overlap_tokens=_env_int("RAG_CHUNK_OVERLAP", 64),
        n_threads=_env_int("RAG_N_THREADS", max(1, (os.cpu_count() or 4) - 1)),
        n_ctx=_env_int("RAG_N_CTX", 4096),
        temperature=_env_float("RAG_TEMPERATURE", 0.2),
        top_p=_env_float("RAG_TOP_P", 0.9),
        api_key=os.getenv("RAG_API_KEY") or None,
        telemetry_path=_env_path("RAG_TELEMETRY_PATH", "data/rag/telemetry.jsonl"),
        feedback_path=_env_path("RAG_FEEDBACK_PATH", "data/rag/feedback.csv"),
    )
