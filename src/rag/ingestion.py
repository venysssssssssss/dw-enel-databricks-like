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
import os
import re
import zipfile
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

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
_CLUSTER_DICTIONARY_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


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


def _env_enabled(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_cluster_dictionary_chunks(path: Path) -> list[Chunk]:
    rows = _read_cluster_dictionary_rows(path)
    chunks: list[Chunk] = []
    source_path = str(path).replace("\\", "/")
    for cluster, terms in rows:
        if not cluster or not terms:
            continue
        anchor = f"cluster-dictionary-{_slug(cluster)}"
        text = (
            f"# Dicionário de cluster: {cluster}\n\n"
            f"- **Cluster**: {cluster}\n"
            f"- **Termos e expressões-chave**: {terms}\n\n"
            "Use este dicionário para expandir consultas de SP e conectar "
            "variações narrativas ao cluster operacional correspondente."
        )
        chunk_key = f"{source_path}::{anchor}::{terms[:120]}"
        chunks.append(
            Chunk(
                chunk_id=hashlib.sha256(chunk_key.encode()).hexdigest()[:16],
                text=text,
                source_path=source_path,
                section=f"Dicionário de cluster · {cluster}",
                doc_type="cluster_dictionary",
                sprint_id="27",
                token_count=_approx_tokens(text),
                anchor=anchor,
                region="SP",
                scope="regional",
                data_source="xlsx.descricoes_enel.cluster_dictionary",
            )
        )
    return chunks


def _read_cluster_dictionary_rows(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        sheets = workbook.find(f"{_CLUSTER_DICTIONARY_NS}sheets")
        if sheets is None or not list(sheets):
            return []
        first_sheet = list(sheets)[0]
        rel_id = first_sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        target = rel_map.get(rel_id)
        if not target:
            return []
        shared_strings = _read_shared_strings(archive)
        root = ET.fromstring(archive.read(f"xl/{target}"))
        sheet_data = root.find(f"{_CLUSTER_DICTIONARY_NS}sheetData")
        if sheet_data is None:
            return []
        rows: list[tuple[str, str]] = []
        for row in list(sheet_data)[1:]:
            values = [_sheet_cell_value(cell, shared_strings) for cell in list(row)]
            if len(values) < 2:
                continue
            cluster = values[0].strip()
            terms = values[1].strip()
            if cluster and terms:
                rows.append((cluster, terms))
        return rows


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    name = "xl/sharedStrings.xml"
    if name not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(name))
    return [
        "".join(text_node.text or "" for text_node in item.iter(f"{_CLUSTER_DICTIONARY_NS}t"))
        for item in root
    ]


def _sheet_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    raw = cell.find(f"{_CLUSTER_DICTIONARY_NS}v")
    if raw is None or raw.text is None:
        return ""
    if cell_type == "s":
        try:
            return shared_strings[int(raw.text)]
        except (IndexError, ValueError):
            return ""
    return raw.text


def _external_rag_chunks(config: RagConfig) -> list[Chunk]:
    chunks: list[Chunk] = []
    if getattr(config, "corpus_include_descricoes_clusters", True) and _env_enabled(
        "RAG_CORPUS_INCLUDE_DESCRICOES_CLUSTERS",
        True,
    ):
        csv_path = Path("DESCRICOES_ENEL/erro_leitura_clusterizado.csv")
        if csv_path.exists():
            try:
                from scripts.build_descricoes_corpus import _read_csv, build_chunks

                rows = _read_csv(csv_path)
                for spec in build_chunks(rows):
                    metadata = spec.metadata
                    chunks.append(
                        Chunk(
                            chunk_id=spec.chunk_id,
                            text=spec.text,
                            source_path=str(metadata.get("source_path", csv_path)).replace(
                                "\\", "/"
                            ),
                            section=spec.section,
                            doc_type=str(metadata.get("doc_type", "descricoes_clusterizadas")),
                            sprint_id=str(metadata.get("sprint_id", "27")),
                            token_count=_approx_tokens(spec.text),
                            anchor=spec.anchor,
                            dataset_version=str(metadata.get("dataset_version", "")),
                            region=str(metadata.get("region", "SP")),
                            scope=str(metadata.get("scope", "regional")),
                            data_source=str(
                                metadata.get(
                                    "data_source",
                                    "csv.descricoes_enel.erro_leitura_clusterizado",
                                )
                            ),
                        )
                    )
            except Exception:
                pass
    if getattr(config, "corpus_include_cluster_dictionary", True) and _env_enabled(
        "RAG_CORPUS_INCLUDE_CLUSTER_DICTIONARY",
        True,
    ):
        try:
            chunks.extend(
                build_cluster_dictionary_chunks(Path("DESCRICOES_ENEL/Dicionário_clusters.xlsx"))
            )
        except Exception:
            pass
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

    all_chunks.extend(_external_rag_chunks(config))

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
    usamos esse modelo; se apontar para um diretório ONNX, usamos a engine ultrarrápida
    em Rust (enel_core.OnnxEmbedder). Se a dependência/modelo não estiver disponível,
    caímos para hashing sem quebrar o chat, exceto quando
    `RAG_REQUIRE_ONNX_EMBEDDING=1` estiver ativo.
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

    # Via Rust ONNX (Performance extrema CPU), com fallback Python/onnxruntime.
    if "onnx" in model_name.lower():
        onnx_error: Exception | None = None
        try:
            import enel_core

            # model_name deve ser o caminho do diretório contendo model.onnx e tokenizer.json
            embedder = enel_core.OnnxEmbedder(model_name)

            def rust_onnx_embed(texts: list[str]) -> list[list[float]]:
                return embedder.embed(texts)

            return rust_onnx_embed
        except Exception as exc:
            onnx_error = exc
            try:
                return _load_python_onnx_embedder(model_name)
            except Exception as python_exc:
                onnx_error = python_exc

            if os.getenv("RAG_REQUIRE_ONNX_EMBEDDING", "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }:
                raise RuntimeError(
                    "RAG_REQUIRE_ONNX_EMBEDDING=1, mas o modelo ONNX "
                    f"não pôde ser carregado de {model_name!r}: {onnx_error}"
                ) from onnx_error
            print(
                "Aviso: falha ao carregar modelo ONNX "
                f"({onnx_error}). Caindo para SentenceTransformers/Hashing."
            )

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)

        def embed(texts: list[str]) -> list[list[float]]:
            arr = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return [list(map(float, row)) for row in arr]

        return embed
    except Exception:  # pragma: no cover - fallback em ambiente sem ST
        return _hashing_embedder()


def _load_python_onnx_embedder(model_name: str):
    """Carrega embedder ONNX puro Python para ambientes sem enel_core."""
    import numpy as np
    import onnxruntime as ort
    from transformers import AutoTokenizer

    model_dir = Path(model_name)
    model_path = model_dir / "model.onnx"
    if not model_path.exists():
        raise FileNotFoundError(model_path)

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = _env_positive_int("RAG_ONNX_INTRA_OP_THREADS", 2)
    session_options.inter_op_num_threads = _env_positive_int("RAG_ONNX_INTER_OP_THREADS", 1)
    session = ort.InferenceSession(
        str(model_path),
        sess_options=session_options,
        providers=["CPUExecutionProvider"],
    )
    input_names = [item.name for item in session.get_inputs()]
    output_names = [item.name for item in session.get_outputs()]
    batch_size = _env_positive_int("RAG_ONNX_BATCH_SIZE", 16)

    def embed(texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        batches: list[list[list[float]]] = []
        for start in range(0, len(texts), batch_size):
            batches.append(_embed_onnx_batch(texts[start : start + batch_size]))
        return [vector for batch in batches for vector in batch]

    def _embed_onnx_batch(batch_texts: list[str]) -> list[list[float]]:
        encoded = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        inputs = {
            name: encoded[name].astype("int64")
            for name in input_names
            if name in encoded
        }
        outputs = dict(zip(output_names, session.run(output_names, inputs), strict=True))
        if "sentence_embedding" in outputs:
            vectors = outputs["sentence_embedding"]
        else:
            token_embeddings = outputs["last_hidden_state"]
            attention_mask = encoded["attention_mask"].astype("float32")
            mask = np.expand_dims(attention_mask, axis=-1)
            vectors = np.sum(token_embeddings * mask, axis=1)
            vectors = vectors / np.clip(np.sum(mask, axis=1), a_min=1e-9, a_max=None)

        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / np.where(norms == 0.0, 1.0, norms)
        return vectors.astype("float32").tolist()

    return embed


def _env_positive_int(key: str, default: int) -> int:
    raw = os.getenv(key, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


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
