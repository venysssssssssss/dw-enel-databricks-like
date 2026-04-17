"""Ingestão do corpus RAG: descobre arquivos, fatia em chunks e indexa no ChromaDB.

Decisões de design:
- **Corpus**: `docs/**/*.md` + `README.md` + `CLAUDE.md`. Sem código-fonte (ruído).
- **Chunker**: 2 estágios — split por header Markdown, depois split por caracteres
  (~480 tokens ~= 1920 chars, overlap 64 tokens). Preserva cabeçalho como metadata
  para citação hierárquica (`docs/business-rules/glossario.md#acf-asf`).
- **Embeddings**: MiniLM multilíngue por default; fallback hashing local
  determinístico quando `sentence-transformers` não está disponível.
- **Store**: ChromaDB PersistentClient (SQLite-backed). Metadata rica permite
  filtragem por `doc_type` antes do vetor.
"""

from __future__ import annotations

import hashlib
import math
import re
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.rag.config import RagConfig

_HEADER_RE = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)
_EMBED_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
_CHARS_PER_TOKEN = 4  # aproximação barata; evita depender de tiktoken em CPU
_HASH_EMBED_DIM = 256
_DOC_TYPE_MAP: dict[str, str] = {
    "sprints": "sprint",
    "business-rules": "business",
    "architecture": "architecture",
    "ml": "ml",
    "api": "api",
    "viz": "viz",
    "implementation": "implementation",
}


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_id: str
    text: str
    source_path: str
    section: str
    doc_type: str
    sprint_id: str
    token_count: int
    anchor: str
    dataset_version: str = ""
    region: str = "CE+SP"
    scope: str = "global"
    data_source: str = "docs.markdown"


@dataclass(slots=True)
class IngestionStats:
    files_scanned: int = 0
    chunks_created: int = 0
    tokens_indexed: int = 0
    skipped: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "files_scanned": self.files_scanned,
            "chunks_created": self.chunks_created,
            "tokens_indexed": self.tokens_indexed,
            "skipped": list(self.skipped),
        }


def discover_files(roots: Iterable[Path]) -> list[Path]:
    """Enumera arquivos Markdown elegíveis, deduplicado por caminho absoluto."""
    seen: set[Path] = set()
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() == ".md":
            files.append(root.resolve())
            seen.add(root.resolve())
            continue
        for md in root.rglob("*.md"):
            absolute = md.resolve()
            if absolute in seen:
                continue
            seen.add(absolute)
            files.append(absolute)
    return sorted(files)


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _infer_doc_type(path: Path) -> str:
    parts = [p.lower() for p in path.parts]
    for key, value in _DOC_TYPE_MAP.items():
        if key in parts:
            return value
    if path.name.lower() in {"readme.md", "claude.md"}:
        return "root"
    return "misc"


def _infer_sprint_id(path: Path) -> str:
    match = re.search(r"sprint[-_ ]?(\d+)", path.stem.lower())
    return f"sprint-{int(match.group(1)):02d}" if match else ""


def _slug(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_]+", "-", slug)[:64]


def _split_by_header(text: str) -> list[tuple[str, str]]:
    """Retorna [(header, body)]. Se sem headers, um único bloco com header vazio."""
    positions = [(m.start(), m.group(2).strip()) for m in _HEADER_RE.finditer(text)]
    if not positions:
        return [("", text)]
    blocks: list[tuple[str, str]] = []
    for i, (start, header) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        body = text[start:end].strip()
        blocks.append((header, body))
    return blocks


def _split_by_chars(
    text: str, *, max_chars: int, overlap_chars: int
) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    stride = max(1, max_chars - overlap_chars)
    return [
        text[i : i + max_chars]
        for i in range(0, len(text), stride)
        if text[i : i + max_chars].strip()
    ]


def chunk_markdown(
    *,
    path: Path,
    content: str,
    chunk_size_tokens: int,
    overlap_tokens: int,
    project_root: Path,
) -> list[Chunk]:
    max_chars = chunk_size_tokens * _CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * _CHARS_PER_TOKEN
    doc_type = _infer_doc_type(path)
    sprint_id = _infer_sprint_id(path)
    try:
        rel_path = path.relative_to(project_root)
    except ValueError:
        rel_path = path
    rel_str = str(rel_path).replace("\\", "/")

    chunks: list[Chunk] = []
    for header, block in _split_by_header(content):
        pieces = _split_by_chars(block, max_chars=max_chars, overlap_chars=overlap_chars)
        for idx, piece in enumerate(pieces):
            piece = piece.strip()
            if len(piece) < 40:
                continue
            anchor = _slug(header) if header else f"c{idx}"
            chunk_key = f"{rel_str}::{anchor}::{idx}::{piece[:120]}"
            chunk_id = hashlib.sha256(chunk_key.encode()).hexdigest()[:16]
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=piece,
                    source_path=rel_str,
                    section=header or "(sem título)",
                    doc_type=doc_type,
                    sprint_id=sprint_id,
                    token_count=_approx_tokens(piece),
                    anchor=anchor,
                )
            )
    return chunks


def build_corpus(config: RagConfig, *, rebuild: bool = False) -> IngestionStats:
    """Ingestão idempotente. Com `rebuild=True` recria a coleção do zero."""
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "chromadb não instalado. Rode: pip install -e '.[rag]' ou pip install chromadb"
        ) from exc

    project_root = Path(config.corpus_roots[0]).parent if config.corpus_roots else Path.cwd()
    config.chromadb_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(config.chromadb_path))

    if rebuild:
        with suppress(Exception):
            client.delete_collection(config.collection_name)

    collection = client.get_or_create_collection(
        name=config.collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    files = discover_files(config.corpus_roots)
    stats = IngestionStats()
    stats.files_scanned = len(files)

    all_chunks: list[Chunk] = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            stats.skipped.append(f"{f}: {exc}")
            continue
        all_chunks.extend(
            chunk_markdown(
                path=f,
                content=content,
                chunk_size_tokens=config.chunk_size_tokens,
                overlap_tokens=config.chunk_overlap_tokens,
                project_root=project_root,
            )
        )

    try:
        from src.data_plane import DataStore
        from src.data_plane.cards import build_data_cards

        data_chunks = build_data_cards(
            DataStore(),
            regional_scope=config.regional_scope,
        )
        all_chunks.extend(data_chunks)
    except Exception as exc:  # pragma: no cover - não-crítico
        stats.skipped.append(f"data_cards: {exc}")

    if not all_chunks:
        return stats

    embedder = _load_embedder(config.embedding_model)
    texts = [c.text for c in all_chunks]
    vectors = embedder(texts)

    now = datetime.now(UTC).isoformat()
    metadatas = [
        {
            "source_path": c.source_path,
            "section": c.section,
            "doc_type": c.doc_type,
            "sprint_id": c.sprint_id,
            "token_count": c.token_count,
            "anchor": c.anchor,
            "dataset_version": c.dataset_version,
            "region": c.region,
            "scope": c.scope,
            "data_source": c.data_source,
            "indexed_at": now,
        }
        for c in all_chunks
    ]

    collection.upsert(
        ids=[c.chunk_id for c in all_chunks],
        embeddings=vectors,
        documents=texts,
        metadatas=metadatas,
    )

    stats.chunks_created = len(all_chunks)
    stats.tokens_indexed = sum(c.token_count for c in all_chunks)
    return stats


def _load_embedder(model_name: str):
    """Retorna callable texts -> List[List[float]].

    `hashing` é o backend default porque é stateless: indexação e consulta sempre
    geram vetores com a mesma dimensão, inclusive dentro do container Streamlit.
    Se `RAG_EMBEDDING_MODEL` apontar para um modelo SentenceTransformer instalado,
    usamos esse modelo; se a dependência/modelo não estiver disponível, caímos para
    hashing sem quebrar o chat.
    """
    if model_name.strip().lower() in {"", "hashing", "hash", "local-hashing", "stub"}:
        try:
            import enel_core

            def rust_embed(texts: list[str]) -> list[list[float]]:
                result = enel_core.hash_embed(texts, _HASH_EMBED_DIM)
                return [list(map(float, row)) for row in result]

            return rust_embed
        except Exception:
            pass
        return _hashing_embedder()

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)

        def embed(texts: list[str]) -> list[list[float]]:
            arr = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return [list(map(float, row)) for row in arr]

        return embed
    except Exception:  # pragma: no cover - fallback em ambiente sem ST
        return _hashing_embedder()


def _hashing_embedder():
    """Embedder lexical stateless de 256 dimensões, sem dependências pesadas."""

    def embed(texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * _HASH_EMBED_DIM
            for token in _EMBED_TOKEN_RE.findall(text.lower()):
                if len(token) <= 2:
                    continue
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                bucket = int.from_bytes(digest[:4], "little") % _HASH_EMBED_DIM
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[bucket] += sign
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            vectors.append([value / norm for value in vector])
        return vectors

    return embed
