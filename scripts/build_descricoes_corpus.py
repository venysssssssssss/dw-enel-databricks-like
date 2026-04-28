"""Index DESCRICOES_ENEL/erro_leitura_clusterizado.csv into the RAG corpus.

Generates two passage families per cluster:
  1. summary card — counts, procedência split, top medidor/canal, anchored
     as `descricoes-cluster-<slug>`.
  2. exemplar passages — top representative real complaint texts (already PII-safe
     in the source CSV: phone numbers stripped on ingestion); anchored as
     `descricoes-exemplo-<slug>-<i>`.

Region: SP only (the CSV is São Paulo). doc_type: `descricoes_clusterizadas`.
Indexes into the same Chroma collection used by docs (`enel_docs`) so
HybridRetriever picks them up automatically through metadata filtering.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.config import load_rag_config  # noqa: E402

CSV_DEFAULT = ROOT / "DESCRICOES_ENEL" / "erro_leitura_clusterizado.csv"
DOC_TYPE = "descricoes_clusterizadas"
REGION = "SP"
DATA_SOURCE = "csv.descricoes_enel.erro_leitura_clusterizado"
SOURCE_PATH = "DESCRICOES_ENEL/erro_leitura_clusterizado.csv"
SPRINT_ID = "27"

_PII_PHONE_RE = re.compile(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}-?\d{4}\b")
_PII_CPF_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_WHITESPACE_RE = re.compile(r"\s+")


def _slug(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    short = base[:100] or "outro"
    if len(base) <= 100:
        return short
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:6]
    return f"{short}-{digest}"


def _redact(text: str) -> str:
    text = _PII_PHONE_RE.sub("[TELEFONE]", text)
    text = _PII_CPF_RE.sub("[CPF]", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        rows = [{k: (v or "").strip() for k, v in row.items()} for row in reader]
    return rows


@dataclass(slots=True)
class ClusterAggregate:
    cluster_label: str
    rows: list[dict[str, str]]


def _group_by_cluster(rows: list[dict[str, str]]) -> dict[str, ClusterAggregate]:
    groups: dict[str, ClusterAggregate] = {}
    for row in rows:
        label = row.get("clusters") or "Outros/Não Especificado"
        groups.setdefault(label, ClusterAggregate(label, []))
        groups[label].rows.append(row)
    return groups


def _proc_split(rows: list[dict[str, str]]) -> tuple[int, int]:
    proc = sum(1 for r in rows if r.get("Procedencia", "").upper() == "PROCEDENTE")
    improc = sum(1 for r in rows if r.get("Procedencia", "").upper() == "IMPROCEDENTE")
    return proc, improc


def _top_counts(rows: list[dict[str, str]], key: str, limit: int = 5) -> list[tuple[str, int]]:
    return Counter(r.get(key, "") for r in rows if r.get(key)).most_common(limit)


def _build_summary_text(label: str, agg: ClusterAggregate) -> str:
    rows = agg.rows
    total = len(rows)
    proc, improc = _proc_split(rows)
    canal = _top_counts(rows, "Canal")
    medidor = _top_counts(rows, "TIPO MEDIDOR")
    assunto = _top_counts(rows, "ASSUNTO")
    proc_pct = 100 * proc / total if total else 0.0
    improc_pct = 100 * improc / total if total else 0.0
    lines = [
        f"# Cluster de descrições: {label}",
        f"- **Volume**: {total} reclamações reais (regional SP, dataset erro_leitura_clusterizado).",
        f"- **Procedência**: {proc} procedentes ({proc_pct:.1f}%) · {improc} improcedentes ({improc_pct:.1f}%).",
    ]
    if assunto:
        lines.append("- **Assunto líder**: " + ", ".join(f"{a} ({c})" for a, c in assunto))
    if canal:
        lines.append("- **Canais**: " + ", ".join(f"{a} ({c})" for a, c in canal))
    if medidor:
        lines.append("- **Tipo de medidor**: " + ", ".join(f"{a} ({c})" for a, c in medidor))
    lines.append("")
    lines.append(
        "Use este cluster para responder perguntas sobre faturas, leituras divergentes e "
        "problemas físicos no medidor: descreva volume, taxa de procedência e canal "
        "predominante; cite o tipo de medidor mais associado quando relevante."
    )
    return "\n".join(lines)


def _exemplars(rows: list[dict[str, str]], limit: int = 6) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        text = _redact(row.get("texto_completo", ""))
        if len(text) < 80 or len(text) > 1200:
            continue
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        if digest in seen:
            continue
        seen.add(digest)
        out.append(text)
        if len(out) >= limit:
            break
    return out


@dataclass(slots=True)
class ChunkSpec:
    chunk_id: str
    text: str
    anchor: str
    section: str
    metadata: dict[str, str | int]


def build_chunks(rows: list[dict[str, str]]) -> list[ChunkSpec]:
    groups = _group_by_cluster(rows)
    chunks: list[ChunkSpec] = []
    for label, agg in groups.items():
        if len(agg.rows) < 5:
            continue
        slug = _slug(label)
        anchor_summary = f"descricoes-cluster-{slug}"
        summary_text = _build_summary_text(label, agg)
        meta_base = {
            "doc_type": DOC_TYPE,
            "region": REGION,
            "scope": "regional",
            "data_source": DATA_SOURCE,
            "source_path": SOURCE_PATH,
            "sprint_id": SPRINT_ID,
            "dataset_version": "csv-2026-04",
            "cluster_label": label,
            "cluster_slug": slug,
            "row_count": len(agg.rows),
        }
        chunks.append(
            ChunkSpec(
                chunk_id=f"{anchor_summary}::summary",
                text=summary_text,
                anchor=anchor_summary,
                section=f"Descrições · {label}",
                metadata={**meta_base, "anchor": anchor_summary},
            )
        )
        for idx, exemplar in enumerate(_exemplars(agg.rows), start=1):
            anchor_ex = f"descricoes-exemplo-{slug}-{idx}"
            chunks.append(
                ChunkSpec(
                    chunk_id=f"{anchor_ex}::exemplar",
                    text=(
                        f"Exemplo real do cluster '{label}' (SP, redigido para anonimização):\n"
                        f"{exemplar}"
                    ),
                    anchor=anchor_ex,
                    section=f"Descrições · {label} · exemplar {idx}",
                    metadata={**meta_base, "anchor": anchor_ex},
                )
            )
    return chunks


def index_chunks(chunks: list[ChunkSpec], *, rebuild_namespace: bool = True) -> dict[str, int]:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError(
            "chromadb não instalado. Rode: pip install -e '.[rag]' ou pip install chromadb"
        ) from exc

    config = load_rag_config()
    config.chromadb_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(config.chromadb_path))
    collection = client.get_or_create_collection(
        name=config.collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    from src.rag.ingestion import _load_embedder
    from src.rag.retriever import _align_embedder_to_collection

    embed_fn = _load_embedder(config.embedding_model)
    # Garante alinhamento com a coleção persistida (pode ser 256-dim hashing).
    embed_fn = _align_embedder_to_collection(collection, embed_fn)

    if rebuild_namespace:
        try:
            existing = collection.get(where={"doc_type": DOC_TYPE})
            ids = existing.get("ids") or []
            if ids:
                collection.delete(ids=ids)
        except Exception:
            pass

    ids = [c.chunk_id for c in chunks]
    docs = [c.text for c in chunks]
    metas = [
        {
            **c.metadata,
            "section": c.section,
        }
        for c in chunks
    ]
    embeddings = embed_fn(docs)
    collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
    return {"chunks_indexed": len(chunks), "clusters": len({c.metadata["cluster_slug"] for c in chunks})}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=CSV_DEFAULT)
    parser.add_argument("--dry-run", action="store_true", help="Apenas gera chunks sem indexar.")
    parser.add_argument(
        "--keep-namespace",
        action="store_true",
        help="Não remove descrições já indexadas antes de adicionar.",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"[erro] CSV não encontrado: {args.csv}")
        return 2

    rows = _read_csv(args.csv)
    chunks = build_chunks(rows)
    print(f"[descricoes] CSV rows={len(rows)} chunks={len(chunks)} clusters="
          f"{len({c.metadata['cluster_slug'] for c in chunks})}")
    if args.dry_run:
        for c in chunks[:3]:
            print(f"--- {c.anchor} ---\n{c.text[:240]}\n")
        return 0
    stats = index_chunks(chunks, rebuild_namespace=not args.keep_namespace)
    print(f"[descricoes] indexed: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
